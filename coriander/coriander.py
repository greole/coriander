import pytest
import os
from shutil import copytree, ignore_patterns
import subprocess


# FIXME read from cli
# 0 - basic: dont run any solver
# 1 - std:   run only small cases
# 2 - extensive
test_level = 1


def readCase(src):
    def subcontents(path):
        l = []
        for r, d, fs in os.walk(path):
            for f in fs:
                l.append(r + "/" + f)
        return l

    return {'constants': subcontents(src + '/constant'),
            'system': subcontents(src + '/system'),
            'times': [],
            }


def cloneCase(src, dst, modifiable=False, linkMesh=False, symlinks=False):
    """ clone a case and create a new Case instance

        symlinks: dont copy files but link files (not implementd)
    """
    if not os.path.exists(dst):
        try:
            #FIXME scientific notation
            ign = ['log*', 'processor*', 'postProcessing*', '[1-9]*[.]?[0-9]*']
            ign = (ign if not linkMesh else ign + ["constant*polyMesh*"])
            copytree(src, dst, ignore=ignore_patterns(*ign))
            if linkMesh:
                cmd = "ln -s " + "../../" + src + "/constant/polyMesh " + dst + "/constant/polyMesh"
                execute_in_path(".", cmd)

        except Exception as e:
            print(e)
    else:
        print("skipping:", dst)

    return Case(path=dst, modifiable=modifiable, parent=src)

def createBase(basePath, solver, links=None, copyCoriander=True):
    solverName, solverDigest = solver
    solverPath = "Solver-" + solverName
    if not os.path.exists(solverPath):
        os.makedirs(solverPath)

    corianderPath = solverPath + "/.coriander"
    if not os.path.exists(corianderPath):
        os.makedirs(corianderPath)

    execute_in_path(corianderPath, 'echo parent:' + solverDigest + ' > solver')

    copytree(basePath, solverPath + "/" + basePath)

    if copyCoriander:
        execute("cp run*.py " + solverPath)

    if isinstance(links, list):
        for l in links:
            execute_in_path(solverPath, "ln -s ../" + l + " " +l)




class ParameterVariation():


    def __init__(self, base, study_name, func, case_name,
            param, values, linkMesh=False, exe=None):
        # clone base first
        self.func = func
        self.base = (base if isinstance(base, str) else Case(base))

        self.cases = [cloneCase(
                        base,
                        study_name + "/" + case_name + self.value_to_name(k),
                        modifiable=True,
                        linkMesh=linkMesh)
                for k in values]
        # mody cases
        self.resp = [getattr(c, func)({param: v}) for c, v in zip(self.cases, values)]
        if isinstance(exe, list):
            self.execute(exe)

    def map_initial(self, path, src_time="latestTime", dst_time=None):
        [c.map_initial(path, src_time, dst_time) for c in self.cases]

    def value_to_name(self, value):
        """ some values are specified as dicts thus a reasonable name
            needs to be found """
        if isinstance(value, dict):
            key = list(value.keys())[0]
            return "_{}_{}".format(key, value[key]["name"])
        else:
            return "_" + str(value)

    def execute(self, fs):
        for c in self.cases:
            for f in fs:
                c.run(f)

    def apply(self, funcs):
        """ .apply([("funcName", {"file":{"key":"Value"}})])
        """
        for f in funcs:
            if isinstance(f, tuple):
                [getattr(c, f[0])(f[1]) for c in self.cases]
            else:
                [getattr(c, f)() for c in self.cases]


    def apply_all(self, funcs):
        for f in funcs:
           [getattr(c, "apply")(f) for c in self.cases]


    def decompose(self):
        self.apply(["decompose"])

    def reconstruct_sample(self):
        self.apply(["reconstruct"])

    def setScheme(self, repl):
        self.apply([("setScheme", repl)])

    def endTime(self, repl):
        self.apply([("endTime", repl)])

    def setStr(self, repl):
        self.apply([("setStr", repl)])

    def setKey(self, repl):
        self.apply([("setKey", repl)])

    def addKey(self, repl):
        self.apply([("addKey", repl)])

    def controlDict(self, repl):
        """ usage .controlDict({"endTime": 0.1}) """
        self.apply([("controlDict", repl)])


class Case:

    def __init__(self, path, modifiable=None, parent=None):
        self.path = path
        self.parent = parent
        self.coriander_path = os.path.join(self.path, ".coriander")
        self.create_coriander_folder()
        self.modifiable = modifiable
        self.files = ""

    def create_coriander_folder(self):
        if not os.path.exists(self.coriander_path):
                os.makedirs(self.coriander_path)
        execute_in_path(self.path, 'echo parent:' + self.parent + ' > .coriander/parent')


    def map_initial(self, path, src_time="latestTime", dst_time=None, meanToInst=False):
        cmd = "mapFields -consistent -case {} -sourceTime {} {}".format(self.path, src_time, path)
        execute(cmd)

    def setScheme(self, repl):
        """
            Usage setScheme(("ddtSchemes", {"default": backward})
        """
        def findSubDict(cnt, key):
            before, inter = cnt.split(key + "\n{")
            intersplit = inter.split('}')
            value = key + "\n{" + intersplit[0] + "}\n"
            return before, value, "}".join(intersplit[1:])

        def replaceKeys(cnt, key, target):
            before, inter = cnt.split(key)
            intersplit = inter.split(';')
            return "".join([before,
                            key + " " + target + ";",
                            ";".join(intersplit[1:])])

        def find_keys(cnt):
            before, inter = cnt.split(key + "\n{")
            lines = [line.split() for line in inter.split('\n')]
            return [line[0] for line in lines if line and line[0]  != "//"]

        def replaceOFdictValue(cnt, d, key, target):
            before, d, after = findSubDict(cnt, d)
            if not key:
                key = find_keys(d)
            if not isinstance(key, list):
                key = [key]
            for k in key:
                d = replaceKeys(d, k, target)
            return "".join([before, d, after])

        d = list(repl.keys())[0]
        values = repl[d]


        schemesFile = self.path + "/system/fvSchemes"
        cnt = ""
        with open(schemesFile, 'r') as f:
            cnt = "".join(f.readlines())

        for key, value in values.items():
            cnt = replaceOFdictValue(cnt, d, key, value)

        with open(schemesFile, 'w') as f:
            f.write(cnt)

    def addKey(self, d):
        fn = list(d.keys())[0]
        repl = d[fn]
        for k, v in repl.items():
            execute_in_path(self.path, "echo '{}' >> {}".format(v, fn))


    def setKey(self, d):
        """ usage setKey(constant/coalCloudProperties,{parcelsPerSecond:1e6}"""
        fn = list(d.keys())[0]
        repl = d[fn]
        for k, v in repl.items():
            execute_in_path(
                    self.path,
                    subs(k + "[ A-Za-z0-9.\-]*;", k + " " + v + ";", fn))

    def endTime(self, value):
        self.setKey(self, {"system/controlDict":{"endTime": value}})

    def controlDict(self, repl):
        self.setKey({"system/controlDict": repl})

    def setStr(self, d):
        """ usage setKey(constant/coalCloudProperties,{str:val}"""
        fn = list(d.keys())[0]
        repl = d[fn]
        for k, v in repl.items():
            execute_in_path(self.path, subs(k, v, fn))


    def run(self, solver):
        """ run case with given solver """
        print("run")
        execute_in_path(self.path, solver)

    def remesh(self, repl):
        log = os.path.join(".coriander", "blockMesh.log")
        if os.path.exists(log):
            return
        for k, v in repl.items():
            execute_in_path(
                    self.path + "/constant/polyMesh/",
                    subs(k + "[ A-Za-z0-9]*;", k + " " + v + ";", "blockMeshDict"))
        execute_in_path(self.path, "blockMesh > " + log)

    def blockMesh(self):
        log = os.path.join(".coriander", "blockMesh.log")
        execute_in_path(self.path, "blockMesh > " + log)


    @property
    def decomposed(self):
        return os.path.exists(
                os.path.join(
                    self.path,
                    "processor0")
                )

    def decompose(self):
        if not self.decomposed:
            execute_in_path(self.path, "decomposePar")

    def clone(self, target):
        return cloneCase(self.path, target)

    def reconstruct(self, latest_only=False):
        execute_in_path(self.path, "reconstructPar -newTimes")


    def reconstruct_sample(self):
        self.reconstruct()
        self.sample()

    def sample(self, latest_only=False):
        execute_in_path(self.path, "sample")

    def apply(self, func):
        execute_in_path(self.path, func)

    def clean_sets(self):
        execute_in_path(self.path, "rm -rf postProcessing/sets")

    def clean_timesteps(self):
        execute_in_path(self.path, "rm -rf [1-9]?.[0-9]?")
        execute_in_path(self.path, "rm -rf [1-9]*")


blockMesh  = 'blockMesh'
pisoFoam   = 'pisoFoam'
simpleFoam = 'simpleFoam'
mpirun     = "mpirun"

lastIterationCMD = 'grep "^Time" log | tail -n1'

controlDict   = 'system/controlDict'
fvSchemes     = 'system/fvSchemes'
transpProps   = 'constant/transportProperties'
RASproperties = 'constant/RASProperties'
chemistryProperties = 'constant/chemistryProperties'

FOAMVERS = os.environ.get('WM_PROJECT_VERSION',False)
# STUDENTPC = ('tutpc' in os.environ.get('HOSTNAME'))

end = lambda x: 'Time = {}'.format(x)

changeEndTime = lambda x: subs('endTime[ 0-9.]*','endTime {}'.format(x), controlDict)

changeUnits = lambda x, fn: subs('\[\(\(-\| \)*[0-9]*\)*\]','[{}]'.format(x), fn)

changeViscosity = lambda x: subs('nu \[ 0 2 -1 0 0 0 0 \][ 0-9.]*','nu [ 0 2 -1 0 0 0 0 ] {}'.format(x), transpProps)

changeDeltaT = lambda x: subs('deltaT[ ]*1','deltaT {}'.format(x), controlDict)

RASTurbModel = lambda x: subs('RASModel[ A-Za-z]*','RASModel {}'.format(x), RASproperties)

TurbSwitch = lambda x: subs('turbulence[ A-Za-z]*','turbulence {}'.format(x), RASproperties)

chemistrySwitch = lambda x: subs('chemistry [a-z]*','chemistry {}'.format(x), chemistryProperties)

setUniformInternalField = lambda x, fn: subs('internalField[ ]*uniform[ 0-9.]*', 'internalField uniform {}'.format(x), fn)

uniformFixedValue = "{{type fixedValue; value uniform {};}}"
zeroGradientt = "{{type zeroGradient;{}}}"

def setBoundary(bcfield, bcname, bctype, bcvalue):
    return subs(
        "\({}\)".format(bcname) + "[ A-Za-z0-9.;{}]*",
        "\\1 {}".format(bctype.format(bcvalue)),
        bcfield)

def subs(org, new, fn):
    return 'sed -i "s/{}/{}/g" {}'.format(org, new, fn)

def derive_from_file(path, src, dest, units):
    shutil.copyfile(path + src, path + dest)
    execute_in_path(path, changeUnits(units, dest))

def execute_ret_output(cmd):
    return subprocess.getoutput(cmd)

def execute(cmd):
    return subprocess.check_call(cmd, shell=True) == 0

def get_tut_name_from_test_file(fn):
    return fn.replace('test_','').replace('.py','').split('/')[-1].upper() + "/FOAM/"

def execute_in_path(path, cmd, func=execute):
    old_dir = os.getcwd()
    os.chdir(path)
    try:
        ret = func(cmd)
    except:
        ret = False
    os.chdir(old_dir)
    return ret

def runSimulation(case_folder, cmd):
    assert execute_in_path(case_folder, cmd)
    lastIteration = execute_in_path(
            case_folder,
            lastIterationCMD,
            execute_ret_output
    )
    return lastIteration

def create_sol_folder(path):
    src = path + 'Case'
    dst = path + 'Sol'
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst + '/'

def copy_case_basics(src, dest):
    os.mkdir(dest)
    for d in ['/0', '/constant', '/system', '/chemistry']:
        try:
            shutil.copytree(src + d, dest + d)
        except Exception as e:
            print(e)

def test_openfoam_is_sourced():
    assert FOAMVERS

