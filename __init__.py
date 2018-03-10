from binaryninja import *
import struct

class SwitchSection:
	is_compressed = False
	check_hash = False
	sectionData = None
	fileOffset = 0
	memoryOffset = 0
	decompressedSize = 0
	exSize = 0
	
	def decompress(self, data):

		return lz4.block.decompress(data)
		

	def __init__(self, data, is_compressed, check_hash):
		self.is_compressed = is_compressed
		self.check_hash = check_hash

		self.fileOffset = data[0:4]
		self.memoryOffset = data[4:8]
		self.decompressedsize = data[8:12]
		self.exSize = data[12:14]

		self.sectionData = self.decompress(data)
		pass

class SwitchExecutableView(BinaryView):
	"""Nintendo Switch Executable"""
	name = "Switch Executable"
	long_name = "Nintendo Switch Executable"
	sections = []
	should_check_hash = False

	def __init__(self, data):
		BinaryView.__init__(self, file_metadata=data.file, parent_view=data)
		self.raw = data
		self.platform = Architecture["aarch64"].standalone_platform

		header = data[0:0x100]
		print('Header: ' +header.encode('hex'))

		flags = struct.unpack("<I", header[0xC: 0xC + 4])[0]
		print('Flags: ' + "{0:b}".format(flags))

		for i in range(3):
			compressed_size
			is_compressed = flags & (1 << i)
			check_hash = flags & (1 << (i + 3))
			sectionData = header[0x10 * (i + 1): 0x10 * (i + 2)]
			self.sections.append(SwitchSection(sectionData, is_compressed, check_hash))

	@classmethod
	def is_valid_for_data(self, data):
		if data[0:4] == 'NSO0':
			return True
		return False

	def init_common(self):
		pass

	def init_real(self):
		pass

	def perform_is_executable(self):
		return True

	def perform_get_entrypoint(self):
		return 0x0

SwitchExecutableView.register()

