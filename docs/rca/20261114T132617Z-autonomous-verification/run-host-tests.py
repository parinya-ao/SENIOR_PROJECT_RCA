"""Reproduce host discovery with recorded, local C++ toolchain prerequisites."""
import json,os,pathlib,sys,time,unittest
run=pathlib.Path(__file__).resolve().parent;root=run.parents[2]
os.chdir(root);sys.path[:0]=[str(root),str(root/'tests')]
os.environ['PATH']=str(run/'host-bin')+os.pathsep+os.environ['PATH']
class EvidenceResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.passed=[]
    def addSuccess(self,test):
        self.passed.append(test.id());super().addSuccess(test)
suite=unittest.defaultTestLoader.discover(str(root/'tests'));discovered=suite.countTestCases();start=time.monotonic()
result=unittest.TextTestRunner(verbosity=2,resultclass=EvidenceResult).run(suite)
report=dict(discovered=discovered,executed=result.testsRun,passed=len(result.passed),failed=len(result.failures),errors=len(result.errors),skipped=[dict(id=t.id(),reason=reason) for t,reason in result.skipped],passed_ids=result.passed,failures=[dict(id=t.id(),traceback=trace) for t,trace in result.failures+result.errors],elapsed_s=time.monotonic()-start)
(run/'host-tests.json').write_text(json.dumps(report,indent=2));sys.exit(not result.wasSuccessful())
