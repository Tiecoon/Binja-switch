from binaryninja import *
import lz4.block
import struct

def unpack32(x):
	return struct.unpack("<I", x)[0]

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

class SwitchExecutableView(BinaryView):
	"""Nintendo Switch Executable"""
	name = "Switch Executable"
	long_name = "Nintendo Switch Executable"
	sections = []
	should_check_hash = False

	def __init__(self, data):
		BinaryView.__init__(self, file_metadata=data.file, parent_view=data)
		self.raw = data
		self.platform = Architecture['aarch64'].standalone_platform 

		header = data[0:0x100]
		print('Header: ' + header.encode('hex'))

		flags = struct.unpack("<I", header[0xC:0xC + 4])[0]
		print('Flags: ' + "{0:b}".format(flags))

		for i in range(3):
			is_compressed = flags & (1 << i)
			check_hash = flags & (1 << (i + 3))
			sectionData = header[0x10 * (i + 1):0x10 * (i + 2)]
			compressedSize = unpack32(header[0x60 + (i * 0x4) : 0x60 + (i + 1)*0x4])
			self.sections.append(
				SwitchSection(sectionData, is_compressed, check_hash))

			section = self.sections[i]
			compressedData = data[section.fileOffset: section.fileOffset + compressedSize] 
			section.decompressData(compressedData)

		self.init_real()

	@classmethod
	def is_valid_for_data(self, data):
		if data[0:4] == 'NSO0':
			return True
		return False

	def init_common(self):
		pass

	def perform_read(self, addr, length):
		return self.sections[0].sectionData[addr: addr +length]

	def init_real(self):
		sectionStrings = ["text", "data", "rodata"]
		sectionSemantics = [SectionSemantics.ReadOnlyCodeSectionSemantics, SectionSemantics.ReadWriteDataSectionSemantics, SectionSemantics.ReadOnlyDataSectionSemantics]
		for i in range(3):
			self.add_user_section(sectionStrings[i], self.sections[i].memoryOffset, self.sections[i].decompressedSize, sectionSemantics[i])
		self.add_entry_point(self.sections[0].memoryOffset)

	def perform_is_offset_readable(self, offt):
		return True

	def perform_is_executable(self):
		return True

	def perform_get_entrypoint(self):
		return self.sections[0].memoryOffset

SwitchExecutableView.register()

