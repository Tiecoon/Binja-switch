from binaryninja import *
import lz4.block
import struct

def unpack32(x):
	return struct.unpack("<I", x)[0]

def unpack64(x):
	return struct.unpack("<Q", x)[0]

class SwitchSection:
	is_compressed = False
	check_hash = False
	sectionData = None
	fileOffset = 0
	memoryOffset = 0
	decompressedSize = 0
	exSize = 0

	def decompressData(self, data):
		size = struct.pack("<L", self.decompressedSize)
		self.sectionData = lz4.block.decompress(size + data)

	def __init__(self, data, is_compressed, check_hash):
		self.is_compressed = is_compressed
		self.check_hash = check_hash

		print(data.encode('hex'))
		self.fileOffset = unpack32(data[0:4])
		self.memoryOffset = unpack32(data[4:8])
		self.decompressedSize = unpack32(data[8:12])
		self.exSize = unpack32(data[12:16])

	def __repr__(self):
		return '<Section: size=' + hex(self.decompressedSize) + " vmem=" + hex(self.memoryOffset) + ">"

class SwitchExecutableView(BinaryView):
	"""Nintendo Switch Executable"""
	name = "Switch Executable"
	long_name = "Nintendo Switch Executable"
	sections = []
	should_check_hash = False

	def __init__(self, data):

		self.sections = []
		self.should_check_hash = False

		# parse what we need from file 
		self.pre_init(data)

		# setup binaryview
		decompressedData = self.sections[0].sectionData + self.sections[1].sectionData + self.sections[2].sectionData

		# temporary workaround for the case where
		# the file data is not what we want binja to use
		fake_parent = BinaryView.new(data=decompressedData)
		BinaryView.__init__(self, file_metadata=data.file, parent_view=fake_parent)
		self.data = decompressedData

		self.platform = Architecture['aarch64'].standalone_platform 
		self.arch = Architecture['aarch64']

		# give data to binja now
		self.post_init()

	def pre_init(self, data):
		self.header = data[0:0x100]

		self.parseTextDataRodata(data)
		self.checkHashes()
		self.parseDynStr()
		self.parseDynSym()
		print(self.sections)

		self.header = None

	def post_init(self):
		self.init_real()
		self.applyDynStr()
		self.applyDynSym()

	def parseTextDataRodata(self, data):

		flags = struct.unpack("<I", self.header[0xC:0xC + 4])[0]
		print('Flags: ' + "{0:b}".format(flags))

		for i in range(3):
			is_compressed = flags & (1 << i)
			check_hash = flags & (1 << (i + 3))
			sectionData = self.header[0x10 * (i + 1):0x10 * (i + 2)]
			compressedSize = unpack32(self.header[0x60 + (i * 0x4) : 0x60 + (i + 1)*0x4])
			self.sections.append(
				SwitchSection(sectionData, is_compressed, check_hash))

			section = self.sections[i]
			compressedData = data[section.fileOffset: section.fileOffset + compressedSize] 
			section.decompressData(compressedData)

		for i in range(2):
			sec0 = self.sections[i]
			sec1 = self.sections[i + 1]

			sec0len = len(sec0.sectionData)
			
			if sec0len < sec1.memoryOffset:
				self.sections[i].sectionData = self.sections[i].sectionData + '\0' * (sec1.memoryOffset - sec0len)
				print('Appending nulls... ' + str(sec1.memoryOffset - sec0len))
				# i don't fully understand this.

	@classmethod
	def is_valid_for_data(self, data):
		if data[0:4] == 'NSO0':
			return True
		return False

	def init_common(self):
		pass

	def init_real(self):
		self.makeSectionsAndSegments()

		self.add_entry_point(self.sections[0].memoryOffset)

		self.applyDynStr()
		self.applyDynSym()

		self.attemptMod0()

	def parseDynStr(self):
		dynstr = self.header[0x90:0x98]
		print('Dynstr at: ' + dynstr.encode('hex'))

	def parseDynSym(self):
		dynsym = unpack64(self.header[0x98:0xa0])
		print('Dynsym at: ' + hex(dynsym + self.sections[1].memoryOffset))
		pass

	def applyDynStr(self):
		pass
	def applyDynSym(self):
		pass

	def checkHashes(self):
		pass

	def attemptMod0(self):
		mod0Addr = unpack32(self.sections[0].sectionData[4:8])
		print('Found MOD0?: ' + str(mod0Addr))

		if self.data[mod0Addr:mod0Addr+4] != 'MOD0':
			print("Couldn't find mod0 :(")
			return

		print('Found MOD0: ' + self.data[mod0Addr:mod0Addr+4])
		self.parseMod0(self.data[mod0Addr:])

	def makeSectionsAndSegments(self):
		sectionStrings = ["text", "data", "rodata"]
		segflags = [
				(SegmentFlag.SegmentContainsCode | SegmentFlag.SegmentExecutable | SegmentFlag.SegmentReadable, SectionSemantics.ReadOnlyCodeSectionSemantics),
				(SegmentFlag.SegmentContainsData | SegmentFlag.SegmentWritable | SegmentFlag.SegmentReadable, SectionSemantics.ReadWriteDataSectionSemantics), 
				(SegmentFlag.SegmentContainsData | SegmentFlag.SegmentDenyWrite | SegmentFlag.SegmentReadable, SectionSemantics.ReadOnlyDataSectionSemantics)
				]

		len_ = 0
		for i in range(3):
			self.add_user_segment(self.sections[i].memoryOffset, self.sections[i].decompressedSize, len_, self.sections[i].decompressedSize, segflags[i][0])
			self.add_user_section(sectionStrings[i], self.sections[i].memoryOffset, self.sections[i].decompressedSize, segflags[i][1])
			len_ += self.sections[i].decompressedSize

	def parseMod0(self, data):
		pass

	def perform_is_executable(self):
		return True

	def perform_get_entrypoint(self):
		return self.sections[0].memoryOffset

SwitchExecutableView.register()

