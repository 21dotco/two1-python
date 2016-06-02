// Protocol Buffers - Google's data interchange format
// Copyright 2008 Google Inc.  All rights reserved.
// https://developers.google.com/protocol-buffers/
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are
// met:
//
//     * Redistributions of source code must retain the above copyright
// notice, this list of conditions and the following disclaimer.
//     * Redistributions in binary form must reproduce the above
// copyright notice, this list of conditions and the following disclaimer
// in the documentation and/or other materials provided with the
// distribution.
//     * Neither the name of Google Inc. nor the names of its
// contributors may be used to endorse or promote products derived from
// this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
// "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
// LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
// A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
// OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
// SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
// LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
// DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
// THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#ifndef GOOGLE_PROTOBUF_PYTHON_CPP_DESCRIPTOR_POOL_H__
#define GOOGLE_PROTOBUF_PYTHON_CPP_DESCRIPTOR_POOL_H__

#include <Python.h>

#include <google/protobuf/stubs/hash.h>
#include <google/protobuf/descriptor.h>

namespace google {
namespace protobuf {
namespace python {

// Wraps operations to the global DescriptorPool which contains information
// about all messages and fields.
//
// There is normally one pool per process. We make it a Python object only
// because it contains many Python references.
// TODO(amauryfa): See whether such objects can appear in reference cycles, and
// consider adding support for the cyclic GC.
//
// "Methods" that interacts with this DescriptorPool are in the cdescriptor_pool
// namespace.
typedef struct PyDescriptorPool {
  PyObject_HEAD

  DescriptorPool* pool;

  // Make our own mapping to retrieve Python classes from C++ descriptors.
  //
  // Descriptor pointers stored here are owned by the DescriptorPool above.
  // Python references to classes are owned by this PyDescriptorPool.
  typedef hash_map<const Descriptor*, PyObject*> ClassesByMessageMap;
  ClassesByMessageMap* classes_by_descriptor;

  // Store interned descriptors, so that the same C++ descriptor yields the same
  // Python object. Objects are not immortal: this map does not own the
  // references, and items are deleted when the last reference to the object is
  // released.
  // This is enough to support the "is" operator on live objects.
  // All descriptors are stored here.
  hash_map<const void*, PyObject*>* interned_descriptors;

  // Cache the options for any kind of descriptor.
  // Descriptor pointers are owned by the DescriptorPool above.
  // Python objects are owned by the map.
  hash_map<const void*, PyObject*>* descriptor_options;
} PyDescriptorPool;


extern PyTypeObject PyDescriptorPool_Type;

namespace cdescriptor_pool {

// Builds a new DescriptorPool. Normally called only once per process.
PyDescriptorPool* NewDescriptorPool();

// Looks up a message by name.
// Returns a message Descriptor, or NULL if not found.
const Descriptor* FindMessageTypeByName(PyDescriptorPool* self,
                                        const string& name);

// Registers a new Python class for the given message descriptor.
// Returns the message Descriptor.
// On error, returns NULL with a Python exception set.
const Descriptor* RegisterMessageClass(
    PyDescriptorPool* self, PyObject* message_class, PyObject* descriptor);

// The function below are also exposed as methods of the DescriptorPool type.

// Retrieves the Python class registered with the given message descriptor.
//
// Returns a *borrowed* reference if found, otherwise returns NULL with an
// exception set.
PyObject* GetMessageClass(PyDescriptorPool* self,
                          const Descriptor* message_descriptor);

// Looks up a message by name. Returns a PyMessageDescriptor corresponding to
// the field on success, or NULL on failure.
//
// Returns a new reference.
PyObject* FindMessageByName(PyDescriptorPool* self, PyObject* name);

// Looks up a field by name. Returns a PyFieldDescriptor corresponding to
// the field on success, or NULL on failure.
//
// Returns a new reference.
PyObject* FindFieldByName(PyDescriptorPool* self, PyObject* name);

// Looks up an extension by name. Returns a PyFieldDescriptor corresponding
// to the field on success, or NULL on failure.
//
// Returns a new reference.
PyObject* FindExtensionByName(PyDescriptorPool* self, PyObject* arg);

// Looks up an enum type by name. Returns a PyEnumDescriptor corresponding
// to the field on success, or NULL on failure.
//
// Returns a new reference.
PyObject* FindEnumTypeByName(PyDescriptorPool* self, PyObject* arg);

// Looks up a oneof by name. Returns a COneofDescriptor corresponding
// to the oneof on success, or NULL on failure.
//
// Returns a new reference.
PyObject* FindOneofByName(PyDescriptorPool* self, PyObject* arg);

}  // namespace cdescriptor_pool

// Retrieve the global descriptor pool owned by the _message module.
// Returns a *borrowed* reference.
PyDescriptorPool* GetDescriptorPool();

// Initialize objects used by this module.
bool InitDescriptorPool();

}  // namespace python
}  // namespace protobuf

}  // namespace google
#endif  // GOOGLE_PROTOBUF_PYTHON_CPP_DESCRIPTOR_POOL_H__
