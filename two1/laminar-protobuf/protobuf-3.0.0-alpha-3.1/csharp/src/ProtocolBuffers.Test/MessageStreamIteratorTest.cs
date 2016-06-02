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

using System.Collections.Generic;
using System.IO;
using Google.ProtocolBuffers.TestProtos;
using NUnit.Framework;
using NestedMessage = Google.ProtocolBuffers.TestProtos.TestAllTypes.Types.NestedMessage;

namespace Google.ProtocolBuffers
{
    public class MessageStreamIteratorTest
    {
        [Test]
        public void ThreeMessagesInMemory()
        {
            MemoryStream stream = new MemoryStream(MessageStreamWriterTest.ThreeMessageData);
            IEnumerable<NestedMessage> iterator = MessageStreamIterator<NestedMessage>.FromStreamProvider(() => stream);
            List<NestedMessage> messages = new List<NestedMessage>(iterator);

            Assert.AreEqual(3, messages.Count);
            Assert.AreEqual(5, messages[0].Bb);
            Assert.AreEqual(1500, messages[1].Bb);
            Assert.IsFalse(messages[2].HasBb);
        }

        [Test]
        public void ManyMessagesShouldNotTriggerSizeAlert()
        {
            int messageSize = TestUtil.GetAllSet().SerializedSize;
            // Enough messages to trigger the alert unless we've reset the size
            // Note that currently we need to make this big enough to copy two whole buffers,
            // as otherwise when we refill the buffer the second type, the alert triggers instantly.
            int correctCount = (CodedInputStream.BufferSize*2)/messageSize + 1;
            using (MemoryStream stream = new MemoryStream())
            {
                MessageStreamWriter<TestAllTypes> writer = new MessageStreamWriter<TestAllTypes>(stream);
                for (int i = 0; i < correctCount; i++)
                {
                    writer.Write(TestUtil.GetAllSet());
                }
                writer.Flush();

                stream.Position = 0;

                int count = 0;
                foreach (var message in MessageStreamIterator<TestAllTypes>.FromStreamProvider(() => stream)
                    .WithSizeLimit(CodedInputStream.BufferSize*2))
                {
                    count++;
                    TestUtil.AssertAllFieldsSet(message);
                }
                Assert.AreEqual(correctCount, count);
            }
        }
    }
}