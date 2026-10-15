# **************************************************************************
# *
# * Authors:   Blanca Pueche (blanca.pueche@cnb.csis.es)
# *
# * Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
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
import json
import shutil

import os, re
import pyworkflow.protocol.params as params
from pyworkflow.protocol.constants import LEVEL_ADVANCED
from pwem.protocols import EMProtocol
from pyworkflow.object import String

from em3dfold.__init__ import Plugin
from pwem.objects.data import AtomStruct
from em3dfold.constants import EM3DFOLD_DIC
from Bio.PDB import PDBParser, MMCIFParser, PPBuilder, CaPPBuilder
from Bio.SeqUtils import seq1

from em3dfold import EM3DFOLD_DIC


class ProtEM3DFold(EMProtocol):
    """
    Protocol to use EM3DFold model.
    """
    _label = 'EM3DFold modelling'

    # -------------------------- DEFINE param functions ----------------------
    def _defineParams(self, form):
        """ Define the input parameters that will be used.
        Params:
            form: this is the form to be populated with sections and params.
        """
        form.addHidden('useGpu', params.BooleanParam, default=True,
                       label="Use GPU for execution",
                       help="This protocol has both CPU and GPU implementation. Choose one.")

        form.addHidden('gpuList', params.StringParam, default='0',
                       label="Choose GPU IDs",
                       help="Comma-separated GPU devices that can be used.")


        form.addSection(label='Input')
        form.addParam('inputVolume', params.PointerParam, allowsNull=False,
                      pointerClass='Volume',
                      label="Input volume: ",
                      help='Select the electron map of the structure in MRC2014')

        form.addParam('modelingMode', params.EnumParam, choices=['With sequences', 'Without sequences (de novo)'],
                      default=0,
                      label='Modeling mode:',
                      help='Choose whether to provide sequence information or model the map without sequences.')

        group = form.addGroup('Parameters')
        group.addParam( 'buildProtein', params.BooleanParam,
                      default=True, condition='modelingMode==1', label='Build protein:')

        group.addParam('buildDNA', params.BooleanParam,
                      default=True, condition='modelingMode==1', label='Build DNA:')

        group.addParam('buildRNA', params.BooleanParam,
                      default=True, condition='modelingMode==1', label='Build RNA:')


        group.addParam('inputType', params.EnumParam, choices=['AtomStruct', 'fasta file'],
                      default=0, condition='modelingMode==0',
                      label='Structure input type: ',
                      help='Select the structures input type.')

        group.addParam('inputStructure', params.PointerParam, allowsNull=True, condition='modelingMode==0 and inputType==0',
                      pointerClass='AtomStruct',
                      label="Input predicted model: ",
                      help='Select the predicted model. Optional')

        group.addParam('file', params.FileParam, condition='modelingMode==0 and inputType==1',
                      label='FASTA file: ',
                      help='Select the structure fasta file. Can have multiple sequences. Optional')

        group.addParam('outputDenovo', params.BooleanParam, default=False,
                      label='Output de novo model: ', condition='modelingMode==0',
                      help='Option to also get a de novo model output. This model provides each aa with entropy values.')


        form.addParallelSection(threads=4, mpi=1)

    # --------------------------- STEPS functions ------------------------------
    def _insertAllSteps(self):
        if self.modelingMode.get() == 0:
            self._insertFunctionStep(self.prepareInputStep)
        self._insertFunctionStep(self.runEM3DFoldStep)
        self._insertFunctionStep(self.createOutputStep)

    def prepareInputStep(self):
        if self.inputType.get() == 0: #structure input
            self.getFasta()
        else: #fasta file input
            self.divideFastas()

    def runEM3DFoldStep(self):
        outputDir = os.path.abspath(self._getPath())

        args = [
            "--map", os.path.abspath(
                self.inputVolume.get().getFileName()
            ),
            "--output", outputDir
        ]

        if self.modelingMode.get() == 0:
            # Modeling with sequences
            program = "em3dfold build"

            fastaDir = self._getExtraPath('fasta_files')

            fastaFiles = {
                'protein.fasta': '--protein',
                'rna.fasta': '--rna',
                'dna.fasta': '--dna'
            }

            foundFasta = False

            for filename, option in fastaFiles.items():
                fastaPath = os.path.join(fastaDir, filename)

                if os.path.isfile(fastaPath):
                    args.extend([
                        option,
                        os.path.abspath(fastaPath)
                    ])
                    foundFasta = True

            if not foundFasta:
                raise RuntimeError(
                    "No FASTA files were generated or found. "
                    "Please check the input structure or FASTA file."
                )

        else:
            # Modeling without sequences
            program = "em3dfold build_no_seq"

            # Select which molecular components to build.
            if self.buildProtein.get():
                args.append("--protein")
            if self.buildRNA.get():
                args.append("--rna")
            if self.buildDNA.get():
                args.append("--dna")


        if self.useGpu.get():
            args.extend(["--device", str(self.gpuList.get())])
        else:
            args.extend(["--device", 'cpu'])

        Plugin.runCondaCommand(
            self,
            args=" ".join(args),
            condaDic=EM3DFOLD_DIC,
            program=program,
            cwd=os.path.abspath(
                Plugin.getVar(EM3DFOLD_DIC['home'])
            )
        )

    def createOutputStep(self):
        outDir = (self._getPath())

        output = os.path.join(outDir, 'output.cif')
        denovoFile = os.path.join(outDir, 'output_denovo_entropy_scores.cif')

        bestStruct = AtomStruct(filename=output)

        self._defineOutputs(
            outputAtomStruct=bestStruct
        )

        if self.outputDenovo.get():
            denovo = AtomStruct(filename=denovoFile)
            self._defineOutputs(
                outputAtomStructDenovo=denovo
            )



    # --------------------------- INFO functions -----------------------------------
    def _summary(self):
        summary = [""]
        return summary

    def _methods(self):
        methods = []
        return methods

    def _validate(self):
        validations = []
        if not any([
            self.buildProtein.get(),
            self.buildRNA.get(),
            self.buildDNA.get()
        ]):
            validations =[
                "Select at least one molecular component to build."
            ]
        return validations

    def _warnings(self):
        warnings = []
        return warnings

    # --------------------------- UTILS functions -----------------------------------
    def guessEntityType(self, sequence):
        """ Guess if a sequence is DNA, RNA or Protein """
        sequence = sequence.upper().strip()

        protein_only = re.compile(r'[DEFHIKLMPQRVWY]')

        if protein_only.search(sequence):
            return 'protein'

        if 'U' in sequence:
            return 'rna'

        return 'dna'

    def getFasta(self):
        structFile = os.path.abspath(
            self.inputStructure.get().getFileName()
        )
        outDir = self._getExtraPath('fasta_files')
        os.makedirs(outDir, exist_ok=True)

        ext = os.path.splitext(structFile)[1].lower()

        if ext in ('.cif', '.mmcif'):
            parser = MMCIFParser(QUIET=True)
        else:
            parser = PDBParser(QUIET=True)

        structure = parser.get_structure('input', structFile)
        model = next(structure.get_models())

        sequences = {
            'protein': [],
            'dna': [],
            'rna': []
        }

        for chain in model:
            # Extract protein sequences.
            peptides = PPBuilder().build_peptides(chain)
            if peptides:
                for peptide in peptides:
                    sequence = str(peptide.get_sequence())

                    if sequence:
                        entityType = self.guessEntityType(sequence)
                        sequences[entityType].append(
                            (f'chain_{chain.id}', sequence)
                        )
                continue

            # Extract nucleotide sequences from non-protein chains.
            residues = [
                residue for residue in chain.get_residues()
                if residue.id[0] == ' '
            ]
            if not residues:
                continue

            # Convert standard nucleotide residue names to one-letter codes.
            nucleotideMap = {
                'A': 'A', 'C': 'C', 'G': 'G', 'U': 'U',
                'DA': 'A', 'DC': 'C', 'DG': 'G', 'DT': 'T',
                'DI': 'I', 'I': 'I',
            }

            sequence = ''.join(
                nucleotideMap[residue.resname.strip().upper()]
                for residue in residues
                if residue.resname.strip().upper() in nucleotideMap
            )

            if sequence:
                entityType = self.guessEntityType(sequence)
                sequences[entityType].append(
                    (f'chain_{chain.id}', sequence)
                )

        # Write a separate FASTA file for each entity type found.
        fastaFiles = {}

        for entityType, records in sequences.items():
            if not records:
                continue

            fastaPath = os.path.join(outDir, f'{entityType}.fasta')

            with open(fastaPath, 'w') as fasta:
                for chainName, sequence in records:
                    fasta.write(f'>{chainName}\n{sequence}\n')

            fastaFiles[entityType] = fastaPath

    def divideFastas(self):
        inputFile = os.path.abspath(self.file.get())
        outDir = self._getExtraPath('fasta_files')
        os.makedirs(outDir, exist_ok=True)

        sequences = {
            'protein': [],
            'dna': [],
            'rna': []
        }

        # Read the input FASTA file.
        header = None
        sequenceParts = []

        with open(inputFile, 'r') as fasta:
            for line in fasta:
                line = line.strip()

                if not line:
                    continue

                if line.startswith('>'):
                    # Save the previous sequence.
                    if header is not None and sequenceParts:
                        sequence = ''.join(sequenceParts).upper()
                        entityType = self.guessEntityType(sequence)
                        sequences[entityType].append((header, sequence))

                    header = line[1:].strip()
                    sequenceParts = []
                else:
                    sequenceParts.append(line)

        # Save the final sequence.
        if header is not None and sequenceParts:
            sequence = ''.join(sequenceParts).upper()
            entityType = self.guessEntityType(sequence)
            sequences[entityType].append((header, sequence))

        # Write one FASTA file per sequence type.
        fastaFiles = {}

        for entityType, records in sequences.items():
            if not records:
                continue

            fastaPath = os.path.join(outDir, f'{entityType}.fasta')

            with open(fastaPath, 'w') as fasta:
                for header, sequence in records:
                    fasta.write(f'>{header}\n')
                    # Wrap sequences at 80 characters per line.
                    for i in range(0, len(sequence), 80):
                        fasta.write(f'{sequence[i:i + 80]}\n')

            fastaFiles[entityType] = fastaPath

