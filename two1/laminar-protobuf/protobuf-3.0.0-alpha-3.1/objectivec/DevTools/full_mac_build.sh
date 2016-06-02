#!/bin/bash
#
# Helper to do build so you don't have to remember all the steps/args.


set -eu

# Some base locations.
readonly ScriptDir=$(dirname "$(echo $0 | sed -e "s,^\([^/]\),$(pwd)/\1,")")
readonly ProtoRootDir="${ScriptDir}/../.."

printUsage() {
  NAME=$(basename "${0}")
  cat << EOF
usage: ${NAME} [OPTIONS]

This script does the common build steps needed.

OPTIONS:

 General:

   -h, --help
         Show this message
   -c, --clean
         Issue a clean before the normal build.
   -a, --autogen
         Start by rerunning autogen & configure.
   -r, --regenerate-descriptors
         The descriptor.proto is checked in generated, cause it to regenerate.
   -j #, --jobs #
         Force the number of parallel jobs (useful for debugging build issues).
   --skip-xcode
         Skip the invoke of Xcode to test the runtime on both iOS and OS X.
   --skip-xcode-ios
         Skip the invoke of Xcode to test the runtime on iOS.
   --skip-xcode-osx
         Skip the invoke of Xcode to test the runtime on OS X.

EOF
}

header() {
  echo ""
  echo "========================================================================"
  echo "    ${@}"
  echo "========================================================================"
}

# Thanks to libtool, builds can fail in odd ways and since it eats some output
# it can be hard to spot, so force error output if make exits with a non zero.
wrapped_make() {
  set +e  # Don't stop if the command fails.
  make $*
  MAKE_EXIT_STATUS=$?
  if [ ${MAKE_EXIT_STATUS} -ne 0 ]; then
    echo "Error: 'make $*' exited with status ${MAKE_EXIT_STATUS}"
    exit ${MAKE_EXIT_STATUS}
  fi
  set -e
}

NUM_MAKE_JOBS=$(/usr/sbin/sysctl -n hw.ncpu)
if [[ "${NUM_MAKE_JOBS}" -lt 4 ]] ; then
  NUM_MAKE_JOBS=4
fi

DO_AUTOGEN=no
DO_CLEAN=no
REGEN_CPP_DESCRIPTORS=no
DO_XCODE_IOS_TESTS=yes
DO_XCODE_OSX_TESTS=yes
while [[ $# != 0 ]]; do
  case "${1}" in
    -h | --help )
      printUsage
      exit 0
      ;;
    -c | --clean )
      DO_CLEAN=yes
      ;;
    -a | --autogen )
      DO_AUTOGEN=yes
      ;;
    -r | --regenerate-cpp-descriptors )
      REGEN_CPP_DESCRIPTORS=yes
      ;;
    -j | --jobs )
      shift
      NUM_MAKE_JOBS="${1}"
      ;;
    --skip-xcode )
      DO_XCODE_IOS_TESTS=no
      DO_XCODE_OSX_TESTS=no
      ;;
    --skip-xcode-ios )
      DO_XCODE_IOS_TESTS=no
      ;;
    --skip-xcode-osx )
      DO_XCODE_OSX_TESTS=no
      ;;
    -*)
      echo "ERROR: Unknown option: ${1}" 1>&2
      printUsage
      exit 1
      ;;
    *)
      echo "ERROR: Unknown argument: ${1}" 1>&2
      printUsage
      exit 1
      ;;
  esac
  shift
done

# Into the proto dir.
pushd "${ProtoRootDir}"

# if no Makefile, force the autogen.
if [[ ! -f Makefile ]] ; then
  DO_AUTOGEN=yes
fi

if [[ "${DO_AUTOGEN}" == "yes" ]] ; then
  header "Running autogen & configure"
  ./autogen.sh
  ./configure CXXFLAGS="-mmacosx-version-min=10.9 -Wnon-virtual-dtor -Woverloaded-virtual -Wunused-const-variable -Wunused-function"
fi

if [[ "${DO_CLEAN}" == "yes" ]] ; then
  header "Cleaning"
  wrapped_make clean
  if [[ "${DO_XCODE_IOS_TESTS}" == "yes" ]] ; then
    XCODEBUILD_CLEAN_BASE_IOS=(
      xcodebuild
        -project objectivec/ProtocolBuffers_iOS.xcodeproj
        -scheme ProtocolBuffers
    )
  "${XCODEBUILD_CLEAN_BASE_IOS[@]}" -configuration Debug clean
  "${XCODEBUILD_CLEAN_BASE_IOS[@]}" -configuration Release clean
  fi
  if [[ "${DO_XCODE_OSX_TESTS}" == "yes" ]] ; then
    XCODEBUILD_CLEAN_BASE_OSX=(
      xcodebuild
        -project objectivec/ProtocolBuffers_OSX.xcodeproj
        -scheme ProtocolBuffers
    )
  "${XCODEBUILD_CLEAN_BASE_OSX[@]}" -configuration Debug clean
  "${XCODEBUILD_CLEAN_BASE_OSX[@]}" -configuration Release clean
  fi
fi

if [[ "${REGEN_CPP_DESCRIPTORS}" == "yes" ]] ; then
  header "Regenerating the C++ descriptor sources."
  ./generate_descriptor_proto.sh -j "${NUM_MAKE_JOBS}"
fi

header "Building"
# Can't issue these together, when fully parallel, something sometimes chokes
# at random.
wrapped_make -j "${NUM_MAKE_JOBS}" all
wrapped_make -j "${NUM_MAKE_JOBS}" check

header "Ensuring the ObjC descriptors are current."
# Find the newest input file (protos, compiler, and this script).
# (these patterns catch some extra stuff, but better to over sample than under)
readonly NewestInput=$(find \
   src/google/protobuf/*.proto \
   src/.libs src/*.la src/protoc \
   objectivec/generate_descriptors_proto.sh \
      -type f -print0 \
      | xargs -0 stat -f "%m %N" \
      | sort -n | tail -n1 | cut -f2- -d" ")
# Find the oldest output file.
readonly OldestOutput=$(find \
      "${ProtoRootDir}/objectivec/google" \
      -type f -print0 \
      | xargs -0 stat -f "%m %N" \
      | sort -n -r | tail -n1 | cut -f2- -d" ")
# If the newest input is newer than the oldest output, regenerate.
if [[ "${NewestInput}" -nt "${OldestOutput}" ]] ; then
  echo ">> Newest input is newer than oldest output, regenerating."
  objectivec/generate_descriptors_proto.sh -j "${NUM_MAKE_JOBS}"
else
  echo ">> Newest input is older than oldest output, no need to regenerating."
fi

header "Checking on the ObjC Runtime Code"
objectivec/DevTools/pddm_tests.py
if ! objectivec/DevTools/pddm.py --dry-run objectivec/*.[hm] objectivec/Tests/*.[hm] ; then
  echo ""
  echo "Update by running:"
  echo "   objectivec/DevTools/pddm.py objectivec/*.[hm] objectivec/Tests/*.[hm]"
  exit 1
fi

if [[ "${DO_XCODE_IOS_TESTS}" == "yes" ]] ; then
  XCODEBUILD_TEST_BASE_IOS=(
    xcodebuild
      -project objectivec/ProtocolBuffers_iOS.xcodeproj
      -scheme ProtocolBuffers
      # Don't need to worry about form factors or retina/non retina;
      # just pick a mix of OS Versions and 32/64 bit.
      -destination "platform=iOS Simulator,name=iPhone 4s,OS=7.1" # 32bit
      -destination "platform=iOS Simulator,name=iPhone 6,OS=8.3" # 64bit
      -destination "platform=iOS Simulator,name=iPad 2,OS=7.1" # 32bit
      -destination "platform=iOS Simulator,name=iPad Air,OS=8.3" # 64bit
  )
  header "Doing Xcode iOS build/tests - Debug"
  "${XCODEBUILD_TEST_BASE_IOS[@]}" -configuration Debug test
  header "Doing Xcode iOS build/tests - Release"
  "${XCODEBUILD_TEST_BASE_IOS[@]}" -configuration Release test
  # Don't leave the simulator in the developer's face.
  killall "iOS Simulator"
fi
if [[ "${DO_XCODE_OSX_TESTS}" == "yes" ]] ; then
  XCODEBUILD_TEST_BASE_OSX=(
    xcodebuild
      -project objectivec/ProtocolBuffers_OSX.xcodeproj
      -scheme ProtocolBuffers
      # Since the ObjC 2.0 Runtime is required, 32bit OS X isn't supported.
      -destination "platform=OS X,arch=x86_64" # 64bit
  )
  header "Doing Xcode OS X build/tests - Debug"
  "${XCODEBUILD_TEST_BASE_OSX[@]}" -configuration Debug test
  header "Doing Xcode OS X build/tests - Release"
  "${XCODEBUILD_TEST_BASE_OSX[@]}" -configuration Release test
fi
