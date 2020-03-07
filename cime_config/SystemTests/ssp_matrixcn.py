"""

CTSM only test to do the CN-matrix spinup procedure

This is a CLM specific test:
Verifies that spinup works correctly
this test is only valid for CLM compsets

Step 0: Run a cold-start with matrix spinup off
Step 1: Run a fast-mode spinup
Step 2: Run a 2-loop fast-mode spinup
Step 3: Run a slow-mode spinup
Step 4: matrix Spinup off
"""
import shutil, glob, os, sys

if __name__ == '__main__':
   CIMEROOT = os.environ.get("CIMEROOT")
   if CIMEROOT is None:
      CIMEROOT = "../../cime";

   sys.path.append(os.path.join( CIMEROOT, "scripts", "lib"))
   sys.path.append(os.path.join( CIMEROOT, "scripts" ) )

from Tools.standard_script_setup import *
from CIME.XML.standard_module_setup import *
from CIME.SystemTests.system_tests_common import SystemTestsCommon


logger = logging.getLogger(__name__)

class SSP_MatrixCN(SystemTestsCommon):

    # Class data
    nyr_forcing = 2
    # Get different integer multiples of the number of forcing years
    full   = nyr_forcing
    twice  = 2 * nyr_forcing
    thrice = 3 * nyr_forcing
    # Define the settings that will be used for each step
    steps  = ["0",       "1",      "2",      "3",      "4"      ]
    desc   = ["cold",    "fast",   "trans",  "slow",   "normal" ]
    run    = ["startup", "hybrid", "hybrid", "hybrid", "hybrid" ]
    spin   = [False,     True,     True,     True,     False    ]
    stop_n = [5,         thrice,   twice,    thrice,   thrice   ]
    cold   = [True,      False,    False,    False,    False    ]
    iloop  = [-999,      -999,     2,        -999,     -999     ]
    sasu   = [-999,      1,        full,     full,     -999     ]

    def __init__(self, case=None):
        """
        initialize an object interface to the SSP_MatrixCN system test
        """
        expect ( len(self.steps) == len(self.sasu),   "length of steps must be the same as sasu" )
        expect ( len(self.steps) == len(self.spin),   "length of steps must be the same as spin" )
        expect ( len(self.steps) == len(self.desc),   "length of steps must be the same as desc" )
        expect ( len(self.steps) == len(self.cold),   "length of steps must be the same as cold" )
        expect ( len(self.steps) == len(self.run),    "length of steps must be the same as run" )
        expect ( len(self.steps) == len(self.iloop),  "length of steps must be the same as iloop" )
        expect ( len(self.steps) == len(self.stop_n), "length of steps must be the same as stop_n" )

        if case is not None:
          SystemTestsCommon.__init__(self, case)


    def __logger__(self, n=0):
        logger.info("Step {}: {}: doing a {} run for {} years".format( self.steps[n], self.run[n], self.desc[n], self.stop_n[n] )  )
        if ( n+1 < self.n_steps() ):
           logger.info("  writing restarts at end of run")
           logger.info("  short term archiving is on ")

    def n_steps(self):
        return( len(self.steps) )

    def total_years(self):
        ysum = 0
        for nyr in self.stop_n:
           ysum = ysum + nyr

        return( ysum )

    def run_phase(self):
        caseroot = self._case.get_value("CASEROOT")
        orig_case = self._case
        orig_casevar = self._case.get_value("CASE")


        # Get a clone of each step except the last one
        b4last = self.n_steps() - 1
        for n in range(b4last):
           #
           # Clone the main case, and get it setup for the next step
           #
           clone_path( "{}.step{}".format(caseroot,steps[n]) )
           if os.path.exists(clone_path):
               shutil.rmtree(clone_path)
           clone = self._case.create_clone(clone_path, keepexe=True)
           os.chdir(clone_path)
           self._set_active_case(clone)

           self.__logger__(n)

           clone.set_value("RUN_TYPE", run[n] )
           clone.set_value("STOP_N", stop_n[n] )
           if ( cold[n] ):
              clone.set_value("CLM_FORCE_COLDSTART", "on" )
           else:
              clone.set_value("CLM_FORCE_COLDSTART", "off" )
           if ( spin[n] ):
              clone.set_value("CLM_ACCELERATED_SPINUP", "on" )
           else:
              clone.set_value("CLM_ACCELERATED_SPINUP", "off" )

           dout_sr = clone.get_value("DOUT_S_ROOT")
           self._skip_pnl = False
           #
           # Start up from the previous case
           #
           rundir = clone.get_value("RUNDIR")
           if ( n > 0 ):
              clone.set_value("GET_REFCASE", False)
              clone.set_value("RUN_REFCASE", refcase)
              clone.set_value("RUN_REFDATE", refdate)
              for item in glob.glob("{}/*{}*".format(rest_path, refdate)):
                  os.symlink(item, os.path.join(rundir, os.path.basename(item)))

              for item in glob.glob("{}/*rpointer*".format(rest_path)):
                  shutil.copy(item, rundir)
           #
           # Run the case (Archiving off)
           #
           self._case.set_value("DOUT_S", False)
           self._case.flush()
           self.run_indv(suffix=steps[n], st_archive=True)

           #
           # Get the reference case from this step for the next step
           #
           refcase = clone.get_value("CASENAME")
           refdate = run_cmd_no_fail(r'ls -1dt {}/rest/*-00000* | head -1 | sed "s/-00000.*//" | sed "s/^.*rest\///"'.format(dout_sr))
           rest_path = os.path.join(dout_sr, "rest", "{}-{}".format(refdate, refsec))
           refsec = "00000"

        #
        # Last step on original case
        #
        n = self.n_steps() - 1
        #
        # Setup the case to run from the previous clone step
        #
        os.chdir(caseroot)
        self._set_active_case(orig_case)
        self.__logger__(n)
        rundir = self._case.get_value("RUNDIR")
        self._case.set_value("GET_REFCASE", False)
        self._case.set_value("RUN_REFCASE", refcase)
        self._case.set_value("RUN_REFDATE", refdate)
        for item in glob.glob("{}/*{}*".format(rest_path, refdate)):
            os.symlink(item, os.path.join(rundir, os.path.basename(item)))

        for item in glob.glob("{}/*rpointer*".format(rest_path)):
            shutil.copy(item, rundir)
        #
        # Run the case (short term archiving is off)
        #
        self.run_indv()


#
# Unit testing for above
#
import unittest
from CIME.case import Case
from CIME.utils import _LessThanFilter
from argparse  import RawTextHelpFormatter

class test_ssp_matrixcn(unittest.TestCase):

   def setUp( self ):
     self.ssp = SSP_MatrixCN()

   def test_logger( self ):
     # Test the logger
     stream_handler = logging.StreamHandler(sys.stdout)
     logger.addHandler(stream_handler)
     logger.level = logging.DEBUG
     logger.info( "nyr_forcing = {}".format(self.ssp.nyr_forcing) )
     for n in range(self.ssp.n_steps()):
       self.ssp.__logger__(n)
       if ( self.ssp.spin[n] ):
          logger.info( "  isspinup = .true." )
          logger.info( "  nyr_sasu = {}".format(self.ssp.sasu[n]) )
          if ( self.ssp.iloop[n] != -999 ):
             logger.info( "  iloop_avg = {}".format(self.ssp.iloop[n]) )

     logger.info( "Total number of years {}".format( self.ssp.total_years() ) )
     logger.removeHandler(stream_handler)

   def test_n_steps( self ):
       self.assertTrue( self.ssp.n_steps() == 5)

if __name__ == '__main__':
     unittest.main()

