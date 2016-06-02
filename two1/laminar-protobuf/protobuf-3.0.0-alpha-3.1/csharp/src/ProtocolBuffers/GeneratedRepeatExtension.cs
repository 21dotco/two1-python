#region Copyright notice and license

// Protocol Buffers - Google's data interchange format
// Copyright 2008 Google Inc.  All rights reserved.
// http://github.com/jskeet/dotnet-protobufs/
// Original C++/Java/Python code:
// http://code.google.com/p/protobuf/
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

#endregion

using System;
using System.Collections;
using System.Collections.Generic;
using Google.ProtocolBuffers.Descriptors;

namespace Google.ProtocolBuffers
{
    /// <summary>
    /// Class used to represent repeat extensions in generated classes.
    /// </summary>
    public sealed class GeneratedRepeatExtension<TExtensionElement> : GeneratedExtensionBase<IList<TExtensionElement>>
    {
        private GeneratedRepeatExtension(FieldDescriptor field) : base(field, typeof(TExtensionElement))
        {
        }

        public static GeneratedExtensionBase<IList<TExtensionElement>> CreateInstance(FieldDescriptor descriptor)
        {
            if (!descriptor.IsRepeated)
            {
                throw new ArgumentException("Must call GeneratedRepeatExtension.CreateInstance() for repeated types.");
            }
            return new GeneratedRepeatExtension<TExtensionElement>(descriptor);
        }

        /// <summary>
        /// Converts the list to the right type.
        /// TODO(jonskeet): Check where this is used, and whether we need to convert
        /// for primitive types.
        /// </summary>
        /// <param name="value"></param>
        /// <returns></returns>
        public override object FromReflectionType(object value)
        {
            if (Descriptor.MappedType == MappedType.Message ||
                Descriptor.MappedType == MappedType.Enum)
            {
                // Must convert the whole list.
                List<TExtensionElement> result = new List<TExtensionElement>();
                foreach (object element in (IEnumerable) value)
                {
                    result.Add((TExtensionElement) SingularFromReflectionType(element));
                }
                return result;
            }
            else
            {
                return value;
            }
        }
    }
}