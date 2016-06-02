#! /usr/bin/env python
#
# See README for usage instructions.
import glob
import os
import subprocess
import sys

# We must use setuptools, not distutils, because we need to use the
# namespace_packages option for the "google" package.
try:
  from setuptools import setup, Extension, find_packages
except ImportError:
  try:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, Extension, find_packages
  except ImportError:
    sys.stderr.write(
        "Could not import setuptools; make sure you have setuptools or "
        "ez_setup installed.\n"
    )
    raise

from distutils.command.clean import clean as _clean

if sys.version_info[0] == 3:
  # Python 3
  from distutils.command.build_py import build_py_2to3 as _build_py
else:
  # Python 2
  from distutils.command.build_py import build_py as _build_py
from distutils.spawn import find_executable

# Find the Protocol Compiler.
if 'PROTOC' in os.environ and os.path.exists(os.environ['PROTOC']):
  protoc = os.environ['PROTOC']
elif os.path.exists("../src/protoc"):
  protoc = "../src/protoc"
elif os.path.exists("../src/protoc.exe"):
  protoc = "../src/protoc.exe"
elif os.path.exists("../vsprojects/Debug/protoc.exe"):
  protoc = "../vsprojects/Debug/protoc.exe"
elif os.path.exists("../vsprojects/Release/protoc.exe"):
  protoc = "../vsprojects/Release/protoc.exe"
else:
  protoc = find_executable("protoc")


def GetVersion():
  """Gets the version from google/protobuf/__init__.py

  Do not import google.protobuf.__init__ directly, because an installed
  protobuf library may be loaded instead."""

  with open(os.path.join('google', 'protobuf', '__init__.py')) as version_file:
    exec(version_file.read(), globals())
    return __version__


def generate_proto(source, require = True):
  """Invokes the Protocol Compiler to generate a _pb2.py from the given
  .proto file.  Does nothing if the output already exists and is newer than
  the input."""

  if not require and not os.path.exists(source):
    return

  output = source.replace(".proto", "_pb2.py").replace("../src/", "")

  if (not os.path.exists(output) or
      (os.path.exists(source) and
       os.path.getmtime(source) > os.path.getmtime(output))):
    print("Generating %s..." % output)

    if not os.path.exists(source):
      sys.stderr.write("Can't find required file: %s\n" % source)
      sys.exit(-1)

    if protoc is None:
      sys.stderr.write(
          "protoc is not installed nor found in ../src. "
          "Please compile it or install the binary package.\n"
      )
      sys.exit(-1)

    protoc_command = [protoc, "-I../src", "-I.", "--python_out=.", source]
    if subprocess.call(protoc_command) != 0:
      sys.exit(-1)


def GenerateUnittestProtos():
  generate_proto("../src/google/protobuf/map_unittest.proto", False)
  generate_proto("../src/google/protobuf/unittest.proto", False)
  generate_proto("../src/google/protobuf/unittest_custom_options.proto", False)
  generate_proto("../src/google/protobuf/unittest_import.proto", False)
  generate_proto("../src/google/protobuf/unittest_import_public.proto", False)
  generate_proto("../src/google/protobuf/unittest_mset.proto", False)
  generate_proto("../src/google/protobuf/unittest_no_generic_services.proto", False)
  generate_proto("../src/google/protobuf/unittest_proto3_arena.proto", False)
  generate_proto("google/protobuf/internal/descriptor_pool_test1.proto", False)
  generate_proto("google/protobuf/internal/descriptor_pool_test2.proto", False)
  generate_proto("google/protobuf/internal/factory_test1.proto", False)
  generate_proto("google/protobuf/internal/factory_test2.proto", False)
  generate_proto("google/protobuf/internal/import_test_package/inner.proto", False)
  generate_proto("google/protobuf/internal/import_test_package/outer.proto", False)
  generate_proto("google/protobuf/internal/missing_enum_values.proto", False)
  generate_proto("google/protobuf/internal/more_extensions.proto", False)
  generate_proto("google/protobuf/internal/more_extensions_dynamic.proto", False)
  generate_proto("google/protobuf/internal/more_messages.proto", False)
  generate_proto("google/protobuf/internal/test_bad_identifiers.proto", False)
  generate_proto("google/protobuf/pyext/python.proto", False)


class clean(_clean):
  def run(self):
    # Delete generated files in the code tree.
    for (dirpath, dirnames, filenames) in os.walk("."):
      for filename in filenames:
        filepath = os.path.join(dirpath, filename)
        if filepath.endswith("_pb2.py") or filepath.endswith(".pyc") or \
           filepath.endswith(".so") or filepath.endswith(".o") or \
           filepath.endswith('google/protobuf/compiler/__init__.py'):
          os.remove(filepath)
    # _clean is an old-style class, so super() doesn't work.
    _clean.run(self)


class build_py(_build_py):
  def run(self):
    # Generate necessary .proto file if it doesn't exist.
    generate_proto("../src/google/protobuf/descriptor.proto")
    generate_proto("../src/google/protobuf/compiler/plugin.proto")
    GenerateUnittestProtos()

    # Make sure google.protobuf/** are valid packages.
    for path in ['', 'internal/', 'compiler/', 'pyext/']:
      try:
        open('google/protobuf/%s__init__.py' % path, 'a').close()
      except EnvironmentError:
        pass
    # _build_py is an old-style class, so super() doesn't work.
    _build_py.run(self)
  # TODO(mrovner): Subclass to run 2to3 on some files only.
  # Tracing what https://wiki.python.org/moin/PortingPythonToPy3k's
  # "Approach 2" section on how to get 2to3 to run on source files during
  # install under Python 3.  This class seems like a good place to put logic
  # that calls python3's distutils.util.run_2to3 on the subset of the files we
  # have in our release that are subject to conversion.
  # See code reference in previous code review.

if __name__ == '__main__':
  ext_module_list = []
  cpp_impl = '--cpp_implementation'
  if cpp_impl in sys.argv:
    sys.argv.remove(cpp_impl)
    # C++ implementation extension
    ext_module_list.append(
        Extension(
            "google.protobuf.pyext._message",
            glob.glob('google/protobuf/pyext/*.cc'),
            define_macros=[('GOOGLE_PROTOBUF_HAS_ONEOF', '1')],
            include_dirs=[".", "../src"],
            libraries=['protobuf'],
            library_dirs=['../src/.libs'],
        )
    )
    os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'cpp'

  setup(
      name='protobuf',
      version=GetVersion(),
      description='Protocol Buffers',
      long_description="Protocol Buffers are Google's data interchange format",
      url='https://developers.google.com/protocol-buffers/',
      maintainer='protobuf@googlegroups.com',
      maintainer_email='protobuf@googlegroups.com',
      license='New BSD License',
      classifiers=[
          'Programming Language :: Python :: 2.7',
      ],
      namespace_packages=['google'],
      packages=find_packages(
          exclude=[
              'import_test_package',
          ],
      ),
      test_suite='google.protobuf.internal',
      cmdclass={
          'clean': clean,
          'build_py': build_py,
      },
      install_requires=['setuptools'],
      ext_modules=ext_module_list,
  )
