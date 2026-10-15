# **************************************************************************
# *
# * Authors:     Blanca Pueche (blanca.pueche@cnb.csic.es)
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 2 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************
import os
from os.path import join, exists

import pwem
from scipion.install.funcs import InstallHelper

from pyworkflow import SPA, TOMO, MODELLING
from .constants import EM3DFOLD_DIC


_version_ = '0.1'
_logo = ""
_references = ['']




class Plugin(pwem.Plugin):
    _homeVar = EM3DFOLD_DIC['home']
    _pathVars = [EM3DFOLD_DIC['home']]
    _supportedVersions = [EM3DFOLD_DIC['version']]

    @classmethod
    def _defineVariables(cls):
        """ Return and write a variable in the config file.
        """
        cls._defineEmVar(EM3DFOLD_DIC['home'], EM3DFOLD_DIC['name'] + '-' + EM3DFOLD_DIC['version'])

    @classmethod
    def defineBinaries(cls, env, default=True):
        installer = InstallHelper(
            EM3DFOLD_DIC['name'],
            packageHome=cls.getVar(EM3DFOLD_DIC['home']),
            packageVersion=EM3DFOLD_DIC['version']
        )

        env_name = cls.getEnvName(EM3DFOLD_DIC)
        print('HOLA')

        installer.addCommand(
            "git clone https://github.com/huang-laboratory/EM3DFold.git",
            f"{EM3DFOLD_DIC['name']}_cloned"
        ).addCommand(
            # 1. Create the Conda environment using the Scipion versioned name
            f"cd EM3DFold && "
            f"eval \"$(conda shell.bash hook)\" && "
            f"conda env create -n {env_name} -f env.yml",
            f"{EM3DFOLD_DIC['name']}_env_created"
        ).addCommand(
            # 2. Install FlashAttention
            f"cd EM3DFold && "
            f"eval \"$(conda shell.bash hook)\" && "
            f"conda activate {env_name} && "
            f"cd flash_attn_whl && "
            f"bash install_flash_attn.sh",
            f"{EM3DFOLD_DIC['name']}_flash_attn_installed"
        ).addCommand(
            # 3. Install EM3DFold and verify the executable
            f"cd EM3DFold && "
            f"eval \"$(conda shell.bash hook)\" && "
            f"conda activate {env_name} && "
            f"python -m pip install . && "
            f"python -m pip show em3dfold && "
            f"test -x \"$CONDA_PREFIX/bin/em3dfold\" && "
            f"em3dfold --help",
            f"{EM3DFOLD_DIC['name']}_installed"
        ).addCommand(
            # 4. Download weights into the repository
            f"cd EM3DFold && "
            f"eval \"$(conda shell.bash hook)\" && "
            f"conda activate {env_name} && "
            f"trap 'rm -f scripts/download_scipion.sh' EXIT && "
            f"sed 's/em3dfold/{env_name}/g' scripts/download.sh "
            f"> scripts/download_scipion.sh && "
            f"bash scripts/download_scipion.sh \"$(pwd)/weights\" && "
            f"conda deactivate",
            f"{EM3DFOLD_DIC['name']}_weights_downloaded"
        )

        installer.addPackage(
            env,
            dependencies=['conda', 'pip', 'git', 'wget'],
            default=default
        )

    @classmethod
    def getEnvName(cls, packageDictionary):
        """ This function returns the name of the conda enviroment for a given package. """
        return '{}-{}'.format(packageDictionary['name'], packageDictionary['version'])

    @classmethod
    def getEnvActivationCommand(cls, packageDictionary, condaHook=True):
        """ This function returns the conda enviroment activation command for a given package. """
        return '{}conda activate {}'.format(cls.getCondaActivationCmd() if condaHook else '',
                                            cls.getEnvName(packageDictionary))

    @classmethod
    def runCondaCommand(cls, protocol, args, condaDic, program, cwd=None, popen=False, silent=True, retOut=False):
        """ General function to run conda commands """
        result = None
        fullProgram = f'{cls.getEnvActivationCommand(condaDic)} && {program} '
        if not popen and not retOut:
            protocol.runJob(fullProgram, args, env=cls.getEnviron(), cwd=cwd, numberOfThreads=1)
        else:
            if not retOut:
                kwargs = {}
                if silent:
                    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
                run(fullProgram + args, env=cls.getEnviron(), cwd=cwd, shell=True, **kwargs)
            else:
                result = subprocess.check_output(fullProgram + args, cwd=cwd, shell=True, text=True)
        return result


