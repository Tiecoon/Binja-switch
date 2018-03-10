from binaryninja import *

class SwitchExecutableView(BinaryView):
	"""Nintendo Switch Executable"""
	name = "Switch Executable"
	long_name = "Nintendo Switch Executable"

	def __init__(self, data):
		BinaryView.__init__(self, file_metadata=data.file, parent_view=data)
		self.raw = data
		self.platform = Architecture["aarch64"].standalone_platform
		print(Architecture)
		pass

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

