import os

from pyworkflow.tests import BaseTest, setupTestProject, DataSet
from pwem.protocols import ProtImportPdb, ProtImportVolumes

from .. import Plugin
from ..protocols import ProtEM3DFold
from ..utils import assertHandle

class TestEM3DFold(BaseTest):
    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        cls.ds = DataSet.getDataSet('model_building_tutorial')


    @classmethod
    def _runImportPDB(cls, id):
        protImportPDB = cls.newProtocol(
            ProtImportPdb,
            inputPdbData=0,
            pdbId=f'{id}',
        )
        cls.launchProtocol(protImportPDB)
        return protImportPDB

    @classmethod
    def _runImportVolume(cls, id):
        protImpVol = cls.newProtocol(
            ProtImportVolumes,
            importFrom=1,
            emdbId=f'{id}'
        )
        cls.launchProtocol(protImpVol)
        return protImpVol

    def _runEM3DFold(self, pdb, map):
        protEM3DFold = self.newProtocol(ProtEM3DFold)

        protEM3DFold.inputVolume.set(map.outputVolume)
        protEM3DFold.inputStructure.set(pdb.outputPdb)

        self.proj.launchProtocol(protEM3DFold, wait=True)
        return protEM3DFold

    def test(self):
        prot = self._runImportPDB('9r1h')
        mapProt = self._runImportVolume('53509')
        na = self._runImportPDB('23vw')
        mapNa = self._runImportVolume('69299')

        protEM3DFoldProt = self._runEM3DFold(prot, mapProt)
        self._waitOutput(protEM3DFoldProt, 'outputAtomStruct', sleepTime=5)
        assertHandle(self.assertIsNotNone, getattr(protEM3DFoldProt, 'outputAtomStruct', None), cwd=protEM3DFoldProt.getWorkingDir())

        protEM3DFoldNA = self._runEM3DFold(na, mapNa)
        self._waitOutput(protEM3DFoldNA, 'outputAtomStruct', sleepTime=5)
        assertHandle(self.assertIsNotNone, getattr(protEM3DFoldNA, 'outputAtomStruct', None),
                     cwd=protEM3DFoldNA.getWorkingDir())
