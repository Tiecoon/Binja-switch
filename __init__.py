from binaryninja import *
import lz4.block
import struct

def unpack32(x):
	return struct.unpack("<I", x)[0]

def unpack64(x):
	return struct.unpack("<Q", x)[0]

def inpack32(x):
	return struct.unpack("<i", x)[0]

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
	dynstr = []
	dynsym = []

	def __init__(self, data):
		self.sections = []
		self.dynstr = []
		self.dynsym = []

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
		print(self.sections)

		self.checkHashes()

	def post_init(self):
		self.init_real()
		self.header = None

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

		# garbage
		if len(self.sections[0].sectionData) < self.sections[1].memoryOffset:
			self.sections[0].sectionData += '\0' * (self.sections[1].memoryOffset - len(self.sections[0].sectionData))

		if len(self.sections[0].sectionData) + len(self.sections[1].sectionData) < self.sections[2].memoryOffset:
			self.sections[1].sectionData += '\0' * (self.sections[2].memoryOffset - len(self.sections[0].sectionData) - len(self.sections[1].sectionData))
		# end garbage

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

		self.attemptMod0()	

	def checkHashes(self):
		pass

	def attemptMod0(self):
		mod0Addr = unpack32(self.sections[0].sectionData[4:8])
		print('Found MOD0?: ' + str(mod0Addr))

		if self.data[mod0Addr:mod0Addr+4] != 'MOD0':
			print("Couldn't find mod0 :(")
			return

		ddynamic = mod0Addr + inpack32(self.data[mod0Addr + 4: mod0Addr + 8])
		bss = mod0Addr + inpack32(self.data[mod0Addr + 8 : mod0Addr + 12])
		bssEnd = mod0Addr + inpack32(self.data[mod0Addr + 12 : mod0Addr + 16])
		
		print('.dynamic: ' + hex(ddynamic))
		print('.dynamic data: ' + self.data[ddynamic: ddynamic + 100].encode('hex'))
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

	def parseMod0(self, mod):
		# Switch wiki says .dynstr/.dynsym offsets are in the file header
		# I don't really understand them. I'm going to use .dynamic from mod0.
		pass

	def perform_is_executable(self):
		return True

	def perform_get_entrypoint(self):
		return self.sections[0].memoryOffset

SwitchExecutableView.register()

