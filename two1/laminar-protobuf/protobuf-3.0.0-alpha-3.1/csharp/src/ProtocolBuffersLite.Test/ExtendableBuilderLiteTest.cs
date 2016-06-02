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
using System.Collections.Generic;
using Google.ProtocolBuffers.TestProtos;
using NUnit.Framework;

namespace Google.ProtocolBuffers
{
    public class ExtendableBuilderLiteTest
    {
        [Test]
        public void TestHasExtensionT()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder()
                .SetExtension(UnittestLite.OptionalInt32ExtensionLite, 123);

            Assert.IsTrue(builder.HasExtension(UnittestLite.OptionalInt32ExtensionLite));
        }

        [Test]
        public void TestHasExtensionTMissing()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder();
            Assert.IsFalse(builder.HasExtension(UnittestLite.OptionalInt32ExtensionLite));
        }

        [Test]
        public void TestGetExtensionCountT()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder()
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 1)
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 2)
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 3);

            Assert.AreEqual(3, builder.GetExtensionCount(UnittestLite.RepeatedInt32ExtensionLite));
        }

        [Test]
        public void TestGetExtensionCountTEmpty()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder();
            Assert.AreEqual(0, builder.GetExtensionCount(UnittestLite.RepeatedInt32ExtensionLite));
        }

        [Test]
        public void TestGetExtensionTNull()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder();
            string value = builder.GetExtension(UnittestLite.OptionalStringExtensionLite);
            Assert.Null(value);
        }

        [Test]
        public void TestGetExtensionTValue()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder()
                .SetExtension(UnittestLite.OptionalInt32ExtensionLite, 3);

            Assert.AreEqual(3, builder.GetExtension(UnittestLite.OptionalInt32ExtensionLite));
        }

        [Test]
        public void TestGetExtensionTEmpty()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder();
            Assert.AreEqual(0, builder.GetExtension(UnittestLite.RepeatedInt32ExtensionLite).Count);
        }

        [Test]
        public void TestGetExtensionTList()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder()
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 1)
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 2)
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 3);

            IList<int> values = builder.GetExtension(UnittestLite.RepeatedInt32ExtensionLite);
            Assert.AreEqual(3, values.Count);
        }

        [Test]
        public void TestGetExtensionTIndex()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder()
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 0)
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 1)
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 2);

            for (int i = 0; i < 3; i++)
                Assert.AreEqual(i, builder.GetExtension(UnittestLite.RepeatedInt32ExtensionLite, i));
        }

        [Test]
        public void TestGetExtensionTIndexOutOfRange()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder();
            Assert.Throws<ArgumentOutOfRangeException>(() => builder.GetExtension(UnittestLite.RepeatedInt32ExtensionLite, 0));
        }

        [Test]
        public void TestSetExtensionTIndex()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder()
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 0)
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 1)
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 2);

            for (int i = 0; i < 3; i++)
                Assert.AreEqual(i, builder.GetExtension(UnittestLite.RepeatedInt32ExtensionLite, i));

            builder.SetExtension(UnittestLite.RepeatedInt32ExtensionLite, 0, 5);
            builder.SetExtension(UnittestLite.RepeatedInt32ExtensionLite, 1, 6);
            builder.SetExtension(UnittestLite.RepeatedInt32ExtensionLite, 2, 7);

            for (int i = 0; i < 3; i++)
                Assert.AreEqual(5 + i, builder.GetExtension(UnittestLite.RepeatedInt32ExtensionLite, i));
        }

        [Test]
        public void TestSetExtensionTIndexOutOfRange()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder();
            Assert.Throws<ArgumentOutOfRangeException>(() => builder.SetExtension(UnittestLite.RepeatedInt32ExtensionLite, 0, -1));
        }

        [Test]
        public void TestClearExtensionTList()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder()
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 0);
            Assert.AreEqual(1, builder.GetExtensionCount(UnittestLite.RepeatedInt32ExtensionLite));

            builder.ClearExtension(UnittestLite.RepeatedInt32ExtensionLite);
            Assert.AreEqual(0, builder.GetExtensionCount(UnittestLite.RepeatedInt32ExtensionLite));
        }

        [Test]
        public void TestClearExtensionTValue()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder()
                .SetExtension(UnittestLite.OptionalInt32ExtensionLite, 0);
            Assert.IsTrue(builder.HasExtension(UnittestLite.OptionalInt32ExtensionLite));

            builder.ClearExtension(UnittestLite.OptionalInt32ExtensionLite);
            Assert.IsFalse(builder.HasExtension(UnittestLite.OptionalInt32ExtensionLite));
        }

        [Test]
        public void TestIndexedByDescriptor()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder();
            Assert.IsFalse(builder.HasExtension(UnittestLite.OptionalInt32ExtensionLite));

            builder[UnittestLite.OptionalInt32ExtensionLite.Descriptor] = 123;

            Assert.IsTrue(builder.HasExtension(UnittestLite.OptionalInt32ExtensionLite));
            Assert.AreEqual(123, builder.GetExtension(UnittestLite.OptionalInt32ExtensionLite));
        }

        [Test]
        public void TestIndexedByDescriptorAndOrdinal()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder()
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 0);
            Assert.AreEqual(1, builder.GetExtensionCount(UnittestLite.RepeatedInt32ExtensionLite));

            IFieldDescriptorLite f = UnittestLite.RepeatedInt32ExtensionLite.Descriptor;
            builder[f, 0] = 123;

            Assert.AreEqual(1, builder.GetExtensionCount(UnittestLite.RepeatedInt32ExtensionLite));
            Assert.AreEqual(123, builder.GetExtension(UnittestLite.RepeatedInt32ExtensionLite, 0));
        }

        [Test]
        public void TestIndexedByDescriptorAndOrdinalOutOfRange()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder();
            Assert.AreEqual(0, builder.GetExtensionCount(UnittestLite.RepeatedInt32ExtensionLite));

            IFieldDescriptorLite f = UnittestLite.RepeatedInt32ExtensionLite.Descriptor;
            Assert.Throws<ArgumentOutOfRangeException>(() => builder[f, 0] = 123);
        }

        [Test]
        public void TestClearFieldByDescriptor()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder()
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 0);
            Assert.AreEqual(1, builder.GetExtensionCount(UnittestLite.RepeatedInt32ExtensionLite));

            IFieldDescriptorLite f = UnittestLite.RepeatedInt32ExtensionLite.Descriptor;
            builder.ClearField(f);
            Assert.AreEqual(0, builder.GetExtensionCount(UnittestLite.RepeatedInt32ExtensionLite));
        }

        [Test]
        public void TestAddRepeatedFieldByDescriptor()
        {
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder()
                .AddExtension(UnittestLite.RepeatedInt32ExtensionLite, 0);
            Assert.AreEqual(1, builder.GetExtensionCount(UnittestLite.RepeatedInt32ExtensionLite));

            IFieldDescriptorLite f = UnittestLite.RepeatedInt32ExtensionLite.Descriptor;
            builder.AddRepeatedField(f, 123);
            Assert.AreEqual(2, builder.GetExtensionCount(UnittestLite.RepeatedInt32ExtensionLite));
            Assert.AreEqual(123, builder.GetExtension(UnittestLite.RepeatedInt32ExtensionLite, 1));
        }

        [Test]
        public void TestMissingExtensionsLite()
        {
            const int optionalInt32 = 12345678;
            TestAllExtensionsLite.Builder builder = TestAllExtensionsLite.CreateBuilder();
            builder.SetExtension(UnittestLite.OptionalInt32ExtensionLite, optionalInt32);
            builder.AddExtension(UnittestLite.RepeatedDoubleExtensionLite, 1.1);
            builder.AddExtension(UnittestLite.RepeatedDoubleExtensionLite, 1.2);
            builder.AddExtension(UnittestLite.RepeatedDoubleExtensionLite, 1.3);
            TestAllExtensionsLite msg = builder.Build();

            Assert.IsTrue(msg.HasExtension(UnittestLite.OptionalInt32ExtensionLite));
            Assert.AreEqual(3, msg.GetExtensionCount(UnittestLite.RepeatedDoubleExtensionLite));

            byte[] bits = msg.ToByteArray();
            TestAllExtensionsLite copy = TestAllExtensionsLite.ParseFrom(bits);
            Assert.IsFalse(copy.HasExtension(UnittestLite.OptionalInt32ExtensionLite));
            Assert.AreEqual(0, copy.GetExtensionCount(UnittestLite.RepeatedDoubleExtensionLite));
            Assert.AreNotEqual(msg, copy);

            //The lite runtime removes all unknown fields and extensions
            byte[] copybits = copy.ToByteArray();
            Assert.AreEqual(0, copybits.Length);
        }

        [Test]
        public void TestMissingFieldsLite()
        {
            TestAllTypesLite msg = TestAllTypesLite.CreateBuilder()
                .SetOptionalInt32(123)
                .SetOptionalString("123")
                .Build();

            byte[] bits = msg.ToByteArray();
            IMessageLite copy = TestAllExtensionsLite.ParseFrom(bits);
            Assert.AreNotEqual(msg, copy);

            //The lite runtime removes all unknown fields and extensions
            byte[] copybits = copy.ToByteArray();
            Assert.AreEqual(0, copybits.Length);
        }
    }
}