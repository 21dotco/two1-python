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

package com.google.protobuf;

import com.google.protobuf.Descriptors.FieldDescriptor;
import map_test.MapForProto2TestProto.TestMap;
import map_test.MapForProto2TestProto.TestMap.MessageValue;
import map_test.MapForProto2TestProto.TestMap.MessageWithRequiredFields;
import map_test.MapForProto2TestProto.TestRecursiveMap;
import map_test.MapForProto2TestProto.TestUnknownEnumValue;

import junit.framework.TestCase;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Unit tests for map fields in proto2 protos.
 */
public class MapForProto2Test extends TestCase {
  private void setMapValues(TestMap.Builder builder) {
    builder.getMutableInt32ToInt32Field().put(1, 11);
    builder.getMutableInt32ToInt32Field().put(2, 22);
    builder.getMutableInt32ToInt32Field().put(3, 33);

    builder.getMutableInt32ToStringField().put(1, "11");
    builder.getMutableInt32ToStringField().put(2, "22");
    builder.getMutableInt32ToStringField().put(3, "33");
    
    builder.getMutableInt32ToBytesField().put(1, TestUtil.toBytes("11"));
    builder.getMutableInt32ToBytesField().put(2, TestUtil.toBytes("22"));
    builder.getMutableInt32ToBytesField().put(3, TestUtil.toBytes("33"));
    
    builder.getMutableInt32ToEnumField().put(1, TestMap.EnumValue.FOO);
    builder.getMutableInt32ToEnumField().put(2, TestMap.EnumValue.BAR);
    builder.getMutableInt32ToEnumField().put(3, TestMap.EnumValue.BAZ);
    
    builder.getMutableInt32ToMessageField().put(
        1, MessageValue.newBuilder().setValue(11).build());
    builder.getMutableInt32ToMessageField().put(
        2, MessageValue.newBuilder().setValue(22).build());
    builder.getMutableInt32ToMessageField().put(
        3, MessageValue.newBuilder().setValue(33).build());
    
    builder.getMutableStringToInt32Field().put("1", 11);
    builder.getMutableStringToInt32Field().put("2", 22);
    builder.getMutableStringToInt32Field().put("3", 33);
  }

  private void assertMapValuesSet(TestMap message) {
    assertEquals(3, message.getInt32ToInt32Field().size());
    assertEquals(11, message.getInt32ToInt32Field().get(1).intValue());
    assertEquals(22, message.getInt32ToInt32Field().get(2).intValue());
    assertEquals(33, message.getInt32ToInt32Field().get(3).intValue());

    assertEquals(3, message.getInt32ToStringField().size());
    assertEquals("11", message.getInt32ToStringField().get(1));
    assertEquals("22", message.getInt32ToStringField().get(2));
    assertEquals("33", message.getInt32ToStringField().get(3));
    
    assertEquals(3, message.getInt32ToBytesField().size());
    assertEquals(TestUtil.toBytes("11"), message.getInt32ToBytesField().get(1));
    assertEquals(TestUtil.toBytes("22"), message.getInt32ToBytesField().get(2));
    assertEquals(TestUtil.toBytes("33"), message.getInt32ToBytesField().get(3));
    
    assertEquals(3, message.getInt32ToEnumField().size());
    assertEquals(TestMap.EnumValue.FOO, message.getInt32ToEnumField().get(1));
    assertEquals(TestMap.EnumValue.BAR, message.getInt32ToEnumField().get(2));
    assertEquals(TestMap.EnumValue.BAZ, message.getInt32ToEnumField().get(3));
    
    assertEquals(3, message.getInt32ToMessageField().size());
    assertEquals(11, message.getInt32ToMessageField().get(1).getValue());
    assertEquals(22, message.getInt32ToMessageField().get(2).getValue());
    assertEquals(33, message.getInt32ToMessageField().get(3).getValue());
    
    assertEquals(3, message.getStringToInt32Field().size());
    assertEquals(11, message.getStringToInt32Field().get("1").intValue());
    assertEquals(22, message.getStringToInt32Field().get("2").intValue());
    assertEquals(33, message.getStringToInt32Field().get("3").intValue());
  }

  private void updateMapValues(TestMap.Builder builder) {
    builder.getMutableInt32ToInt32Field().put(1, 111);
    builder.getMutableInt32ToInt32Field().remove(2);
    builder.getMutableInt32ToInt32Field().put(4, 44);

    builder.getMutableInt32ToStringField().put(1, "111");
    builder.getMutableInt32ToStringField().remove(2);
    builder.getMutableInt32ToStringField().put(4, "44");
    
    builder.getMutableInt32ToBytesField().put(1, TestUtil.toBytes("111"));
    builder.getMutableInt32ToBytesField().remove(2);
    builder.getMutableInt32ToBytesField().put(4, TestUtil.toBytes("44"));
    
    builder.getMutableInt32ToEnumField().put(1, TestMap.EnumValue.BAR);
    builder.getMutableInt32ToEnumField().remove(2);
    builder.getMutableInt32ToEnumField().put(4, TestMap.EnumValue.QUX);
    
    builder.getMutableInt32ToMessageField().put(
        1, MessageValue.newBuilder().setValue(111).build());
    builder.getMutableInt32ToMessageField().remove(2);
    builder.getMutableInt32ToMessageField().put(
        4, MessageValue.newBuilder().setValue(44).build());
    
    builder.getMutableStringToInt32Field().put("1", 111);
    builder.getMutableStringToInt32Field().remove("2");
    builder.getMutableStringToInt32Field().put("4", 44);
  }

  private void assertMapValuesUpdated(TestMap message) {
    assertEquals(3, message.getInt32ToInt32Field().size());
    assertEquals(111, message.getInt32ToInt32Field().get(1).intValue());
    assertEquals(33, message.getInt32ToInt32Field().get(3).intValue());
    assertEquals(44, message.getInt32ToInt32Field().get(4).intValue());

    assertEquals(3, message.getInt32ToStringField().size());
    assertEquals("111", message.getInt32ToStringField().get(1));
    assertEquals("33", message.getInt32ToStringField().get(3));
    assertEquals("44", message.getInt32ToStringField().get(4));
    
    assertEquals(3, message.getInt32ToBytesField().size());
    assertEquals(TestUtil.toBytes("111"), message.getInt32ToBytesField().get(1));
    assertEquals(TestUtil.toBytes("33"), message.getInt32ToBytesField().get(3));
    assertEquals(TestUtil.toBytes("44"), message.getInt32ToBytesField().get(4));
    
    assertEquals(3, message.getInt32ToEnumField().size());
    assertEquals(TestMap.EnumValue.BAR, message.getInt32ToEnumField().get(1));
    assertEquals(TestMap.EnumValue.BAZ, message.getInt32ToEnumField().get(3));
    assertEquals(TestMap.EnumValue.QUX, message.getInt32ToEnumField().get(4));
    
    assertEquals(3, message.getInt32ToMessageField().size());
    assertEquals(111, message.getInt32ToMessageField().get(1).getValue());
    assertEquals(33, message.getInt32ToMessageField().get(3).getValue());
    assertEquals(44, message.getInt32ToMessageField().get(4).getValue());
    
    assertEquals(3, message.getStringToInt32Field().size());
    assertEquals(111, message.getStringToInt32Field().get("1").intValue());
    assertEquals(33, message.getStringToInt32Field().get("3").intValue());
    assertEquals(44, message.getStringToInt32Field().get("4").intValue());
  }

  private void assertMapValuesCleared(TestMap message) {
    assertEquals(0, message.getInt32ToInt32Field().size());
    assertEquals(0, message.getInt32ToStringField().size());
    assertEquals(0, message.getInt32ToBytesField().size());
    assertEquals(0, message.getInt32ToEnumField().size());
    assertEquals(0, message.getInt32ToMessageField().size());
    assertEquals(0, message.getStringToInt32Field().size());
  }
  
  public void testMutableMapLifecycle() {
    TestMap.Builder builder = TestMap.newBuilder();
    Map<Integer, Integer> intMap = builder.getMutableInt32ToInt32Field();
    intMap.put(1, 2);
    assertEquals(newMap(1, 2), builder.build().getInt32ToInt32Field());
    try {
      intMap.put(2, 3);
      fail();
    } catch (UnsupportedOperationException e) {
      // expected
    }
    assertEquals(newMap(1, 2), builder.getInt32ToInt32Field());
    builder.getMutableInt32ToInt32Field().put(2, 3);
    assertEquals(newMap(1, 2, 2, 3), builder.getInt32ToInt32Field());

    Map<Integer, TestMap.EnumValue> enumMap = builder.getMutableInt32ToEnumField();
    enumMap.put(1, TestMap.EnumValue.BAR);
    assertEquals(newMap(1, TestMap.EnumValue.BAR), builder.build().getInt32ToEnumField());
    try {
      enumMap.put(2, TestMap.EnumValue.FOO);
      fail();
    } catch (UnsupportedOperationException e) {
      // expected
    }
    assertEquals(newMap(1, TestMap.EnumValue.BAR), builder.getInt32ToEnumField());
    builder.getMutableInt32ToEnumField().put(2, TestMap.EnumValue.FOO);
    assertEquals(
        newMap(1, TestMap.EnumValue.BAR, 2, TestMap.EnumValue.FOO),
        builder.getInt32ToEnumField());
    
    Map<Integer, String> stringMap = builder.getMutableInt32ToStringField();
    stringMap.put(1, "1");
    assertEquals(newMap(1, "1"), builder.build().getInt32ToStringField());
    try {
      stringMap.put(2, "2");
      fail();
    } catch (UnsupportedOperationException e) {
      // expected
    }
    assertEquals(newMap(1, "1"), builder.getInt32ToStringField());
    builder.getMutableInt32ToStringField().put(2, "2");
    assertEquals(
        newMap(1, "1", 2, "2"),
        builder.getInt32ToStringField());
    
    Map<Integer, TestMap.MessageValue> messageMap = builder.getMutableInt32ToMessageField();
    messageMap.put(1, TestMap.MessageValue.getDefaultInstance());
    assertEquals(newMap(1, TestMap.MessageValue.getDefaultInstance()),
        builder.build().getInt32ToMessageField());
    try {
      messageMap.put(2, TestMap.MessageValue.getDefaultInstance());
      fail();
    } catch (UnsupportedOperationException e) {
      // expected
    }
    assertEquals(newMap(1, TestMap.MessageValue.getDefaultInstance()),
        builder.getInt32ToMessageField());
    builder.getMutableInt32ToMessageField().put(2, TestMap.MessageValue.getDefaultInstance());
    assertEquals(
        newMap(1, TestMap.MessageValue.getDefaultInstance(),
            2, TestMap.MessageValue.getDefaultInstance()),
        builder.getInt32ToMessageField());
  }

  public void testMutableMapLifecycle_collections() {
    TestMap.Builder builder = TestMap.newBuilder();
    Map<Integer, Integer> intMap = builder.getMutableInt32ToInt32Field();
    intMap.put(1, 2);
    assertEquals(newMap(1, 2), builder.build().getInt32ToInt32Field());
    try {
      intMap.remove(2);
      fail();
    } catch (UnsupportedOperationException e) {
      // expected
    }
    try {
      intMap.entrySet().remove(new Object());
      fail();
    } catch (UnsupportedOperationException e) {
      // expected
    }
    try {
      intMap.entrySet().iterator().remove();
      fail();
    } catch (UnsupportedOperationException e) {
      // expected
    }
    try {
      intMap.keySet().remove(new Object());
      fail();
    } catch (UnsupportedOperationException e) {
      // expected
    }
    try {
      intMap.values().remove(new Object());
      fail();
    } catch (UnsupportedOperationException e) {
      // expected
    }
    try {
      intMap.values().iterator().remove();
      fail();
    } catch (UnsupportedOperationException e) {
      // expected
    }
    assertEquals(newMap(1, 2), intMap);
    assertEquals(newMap(1, 2), builder.getInt32ToInt32Field());
    assertEquals(newMap(1, 2), builder.build().getInt32ToInt32Field());
  }

  public void testGettersAndSetters() throws Exception {
    TestMap.Builder builder = TestMap.newBuilder();
    TestMap message = builder.build();
    assertMapValuesCleared(message);
    
    builder = message.toBuilder();
    setMapValues(builder);
    message = builder.build();
    assertMapValuesSet(message);
    
    builder = message.toBuilder();
    updateMapValues(builder);
    message = builder.build();
    assertMapValuesUpdated(message);
    
    builder = message.toBuilder();
    builder.clear();
    message = builder.build();
    assertMapValuesCleared(message);
  }

  public void testSerializeAndParse() throws Exception {
    TestMap.Builder builder = TestMap.newBuilder();
    setMapValues(builder);
    TestMap message = builder.build();
    assertEquals(message.getSerializedSize(), message.toByteString().size());
    message = TestMap.PARSER.parseFrom(message.toByteString());
    assertMapValuesSet(message);
    
    builder = message.toBuilder();
    updateMapValues(builder);
    message = builder.build();
    assertEquals(message.getSerializedSize(), message.toByteString().size());
    message = TestMap.PARSER.parseFrom(message.toByteString());
    assertMapValuesUpdated(message);
    
    builder = message.toBuilder();
    builder.clear();
    message = builder.build();
    assertEquals(message.getSerializedSize(), message.toByteString().size());
    message = TestMap.PARSER.parseFrom(message.toByteString());
    assertMapValuesCleared(message);
  }
  
  public void testMergeFrom() throws Exception {
    TestMap.Builder builder = TestMap.newBuilder();
    setMapValues(builder);
    TestMap message = builder.build();
    
    TestMap.Builder other = TestMap.newBuilder();
    other.mergeFrom(message);
    assertMapValuesSet(other.build());
  }

  public void testEqualsAndHashCode() throws Exception {
    // Test that generated equals() and hashCode() will disregard the order
    // of map entries when comparing/hashing map fields.
    
    // We can't control the order of elements in a HashMap. The best we can do
    // here is to add elements in different order.
    TestMap.Builder b1 = TestMap.newBuilder();
    b1.getMutableInt32ToInt32Field().put(1, 2);
    b1.getMutableInt32ToInt32Field().put(3, 4);
    b1.getMutableInt32ToInt32Field().put(5, 6);
    TestMap m1 = b1.build();
    
    TestMap.Builder b2 = TestMap.newBuilder();
    b2.getMutableInt32ToInt32Field().put(5, 6);
    b2.getMutableInt32ToInt32Field().put(1, 2);
    b2.getMutableInt32ToInt32Field().put(3, 4);
    TestMap m2 = b2.build();
    
    assertEquals(m1, m2);
    assertEquals(m1.hashCode(), m2.hashCode());
    
    // Make sure we did compare map fields.
    b2.getMutableInt32ToInt32Field().put(1, 0);
    m2 = b2.build();
    assertFalse(m1.equals(m2));
    // Don't check m1.hashCode() != m2.hashCode() because it's not guaranteed
    // to be different.
  }
  
  
  // The following methods are used to test reflection API.
  
  private static FieldDescriptor f(String name) {
    return TestMap.getDescriptor().findFieldByName(name);
  }
  
  private static Object getFieldValue(Message mapEntry, String name) {
    FieldDescriptor field = mapEntry.getDescriptorForType().findFieldByName(name);
    return mapEntry.getField(field);
  }
  
  private static Message.Builder setFieldValue(
      Message.Builder mapEntry, String name, Object value) {
    FieldDescriptor field = mapEntry.getDescriptorForType().findFieldByName(name);
    mapEntry.setField(field, value);
    return mapEntry;
  }
  
  private static void assertHasMapValues(Message message, String name, Map<?, ?> values) {
    FieldDescriptor field = f(name);
    for (Object entry : (List<?>) message.getField(field)) {
      Message mapEntry = (Message) entry;
      Object key = getFieldValue(mapEntry, "key");
      Object value = getFieldValue(mapEntry, "value");
      assertTrue(values.containsKey(key));
      assertEquals(value, values.get(key));
    }
    assertEquals(values.size(), message.getRepeatedFieldCount(field));
    for (int i = 0; i < message.getRepeatedFieldCount(field); i++) {
      Message mapEntry = (Message) message.getRepeatedField(field, i);
      Object key = getFieldValue(mapEntry, "key");
      Object value = getFieldValue(mapEntry, "value");
      assertTrue(values.containsKey(key));
      assertEquals(value, values.get(key));
    }
  }
  
  private static <KeyType, ValueType>
  Message newMapEntry(Message.Builder builder, String name, KeyType key, ValueType value) {
    FieldDescriptor field = builder.getDescriptorForType().findFieldByName(name);
    Message.Builder entryBuilder = builder.newBuilderForField(field);
    FieldDescriptor keyField = entryBuilder.getDescriptorForType().findFieldByName("key");
    FieldDescriptor valueField = entryBuilder.getDescriptorForType().findFieldByName("value");
    entryBuilder.setField(keyField, key);
    entryBuilder.setField(valueField, value);
    return entryBuilder.build();
  }
  
  private static void setMapValues(Message.Builder builder, String name, Map<?, ?> values) {
    List<Message> entryList = new ArrayList<Message>();
    for (Map.Entry<?, ?> entry : values.entrySet()) {
      entryList.add(newMapEntry(builder, name, entry.getKey(), entry.getValue()));
    }
    FieldDescriptor field = builder.getDescriptorForType().findFieldByName(name);
    builder.setField(field, entryList);
  }
  
  private static <KeyType, ValueType>
  Map<KeyType, ValueType> mapForValues(
      KeyType key1, ValueType value1, KeyType key2, ValueType value2) {
    Map<KeyType, ValueType> map = new HashMap<KeyType, ValueType>();
    map.put(key1, value1);
    map.put(key2, value2);
    return map;
  }

  public void testReflectionApi() throws Exception {
    // In reflection API, map fields are just repeated message fields.
    TestMap.Builder builder = TestMap.newBuilder();
    builder.getMutableInt32ToInt32Field().put(1, 2);
    builder.getMutableInt32ToInt32Field().put(3, 4);
    builder.getMutableInt32ToMessageField().put(
        11, MessageValue.newBuilder().setValue(22).build());
    builder.getMutableInt32ToMessageField().put(
        33, MessageValue.newBuilder().setValue(44).build());
    TestMap message = builder.build();

    // Test getField(), getRepeatedFieldCount(), getRepeatedField().
    assertHasMapValues(message, "int32_to_int32_field",
        mapForValues(1, 2, 3, 4));
    assertHasMapValues(message, "int32_to_message_field",
        mapForValues(
            11, MessageValue.newBuilder().setValue(22).build(),
            33, MessageValue.newBuilder().setValue(44).build()));
    
    // Test clearField()
    builder.clearField(f("int32_to_int32_field"));
    builder.clearField(f("int32_to_message_field"));
    message = builder.build();
    assertEquals(0, message.getInt32ToInt32Field().size());
    assertEquals(0, message.getInt32ToMessageField().size());
    
    // Test setField()
    setMapValues(builder, "int32_to_int32_field",
        mapForValues(11, 22, 33, 44));
    setMapValues(builder, "int32_to_message_field",
        mapForValues(
            111, MessageValue.newBuilder().setValue(222).build(),
            333, MessageValue.newBuilder().setValue(444).build()));
    message = builder.build();
    assertEquals(22, message.getInt32ToInt32Field().get(11).intValue());
    assertEquals(44, message.getInt32ToInt32Field().get(33).intValue());
    assertEquals(222, message.getInt32ToMessageField().get(111).getValue());
    assertEquals(444, message.getInt32ToMessageField().get(333).getValue());
    
    // Test addRepeatedField
    builder.addRepeatedField(f("int32_to_int32_field"),
        newMapEntry(builder, "int32_to_int32_field", 55, 66));
    builder.addRepeatedField(f("int32_to_message_field"),
        newMapEntry(builder, "int32_to_message_field", 555,
            MessageValue.newBuilder().setValue(666).build()));
    message = builder.build();
    assertEquals(66, message.getInt32ToInt32Field().get(55).intValue());
    assertEquals(666, message.getInt32ToMessageField().get(555).getValue());

    // Test addRepeatedField (overriding existing values)
    builder.addRepeatedField(f("int32_to_int32_field"),
        newMapEntry(builder, "int32_to_int32_field", 55, 55));
    builder.addRepeatedField(f("int32_to_message_field"),
        newMapEntry(builder, "int32_to_message_field", 555,
            MessageValue.newBuilder().setValue(555).build()));
    message = builder.build();
    assertEquals(55, message.getInt32ToInt32Field().get(55).intValue());
    assertEquals(555, message.getInt32ToMessageField().get(555).getValue());
    
    // Test setRepeatedField
    for (int i = 0; i < builder.getRepeatedFieldCount(f("int32_to_int32_field")); i++) {
      Message mapEntry = (Message) builder.getRepeatedField(f("int32_to_int32_field"), i);
      int oldKey = ((Integer) getFieldValue(mapEntry, "key")).intValue();
      int oldValue = ((Integer) getFieldValue(mapEntry, "value")).intValue();
      // Swap key with value for each entry.
      Message.Builder mapEntryBuilder = mapEntry.toBuilder();
      setFieldValue(mapEntryBuilder, "key", oldValue);
      setFieldValue(mapEntryBuilder, "value", oldKey);
      builder.setRepeatedField(f("int32_to_int32_field"), i, mapEntryBuilder.build());
    }
    message = builder.build();
    assertEquals(11, message.getInt32ToInt32Field().get(22).intValue());
    assertEquals(33, message.getInt32ToInt32Field().get(44).intValue());
    assertEquals(55, message.getInt32ToInt32Field().get(55).intValue());
  }
  
  public void testTextFormat() throws Exception {
    TestMap.Builder builder = TestMap.newBuilder();
    setMapValues(builder);
    TestMap message = builder.build();
    
    String textData = TextFormat.printToString(message);
    
    builder = TestMap.newBuilder();
    TextFormat.merge(textData, builder);
    message = builder.build();
    
    assertMapValuesSet(message);
  }
  
  public void testDynamicMessage() throws Exception {
    TestMap.Builder builder = TestMap.newBuilder();
    setMapValues(builder);
    TestMap message = builder.build();
    
    Message dynamicDefaultInstance =
        DynamicMessage.getDefaultInstance(TestMap.getDescriptor());
    Message dynamicMessage = dynamicDefaultInstance
        .newBuilderForType().mergeFrom(message.toByteString()).build();
    
    assertEquals(message, dynamicMessage);
    assertEquals(message.hashCode(), dynamicMessage.hashCode());
  }
  
  public void testReflectionEqualsAndHashCode() throws Exception {
    // Test that generated equals() and hashCode() will disregard the order
    // of map entries when comparing/hashing map fields.

    // We use DynamicMessage to test reflection based equals()/hashCode().
    Message dynamicDefaultInstance =
        DynamicMessage.getDefaultInstance(TestMap.getDescriptor());
    FieldDescriptor field = f("int32_to_int32_field");
    
    Message.Builder b1 = dynamicDefaultInstance.newBuilderForType();
    b1.addRepeatedField(field, newMapEntry(b1, "int32_to_int32_field", 1, 2));
    b1.addRepeatedField(field, newMapEntry(b1, "int32_to_int32_field", 3, 4));
    b1.addRepeatedField(field, newMapEntry(b1, "int32_to_int32_field", 5, 6));
    Message m1 = b1.build();
    
    Message.Builder b2 = dynamicDefaultInstance.newBuilderForType();
    b2.addRepeatedField(field, newMapEntry(b2, "int32_to_int32_field", 5, 6));
    b2.addRepeatedField(field, newMapEntry(b2, "int32_to_int32_field", 1, 2));
    b2.addRepeatedField(field, newMapEntry(b2, "int32_to_int32_field", 3, 4));
    Message m2 = b2.build();
    
    assertEquals(m1, m2);
    assertEquals(m1.hashCode(), m2.hashCode());
    
    // Make sure we did compare map fields.
    b2.setRepeatedField(field, 0, newMapEntry(b1, "int32_to_int32_field", 0, 0));
    m2 = b2.build();
    assertFalse(m1.equals(m2));
    // Don't check m1.hashCode() != m2.hashCode() because it's not guaranteed
    // to be different.
  }
  
  public void testUnknownEnumValues() throws Exception {
    TestUnknownEnumValue.Builder builder =
        TestUnknownEnumValue.newBuilder();
    builder.getMutableInt32ToInt32Field().put(1, 1);
    builder.getMutableInt32ToInt32Field().put(2, 54321);
    ByteString data = builder.build().toByteString();

    TestMap message = TestMap.parseFrom(data);
    // Entries with unknown enum values will be stored into UnknownFieldSet so
    // there is only one entry in the map.
    assertEquals(1, message.getInt32ToEnumField().size());
    assertEquals(TestMap.EnumValue.BAR, message.getInt32ToEnumField().get(1));
    // UnknownFieldSet should not be empty.
    assertFalse(message.getUnknownFields().asMap().isEmpty());
    // Serializing and parsing should preserve the unknown entry.
    data = message.toByteString();
    TestUnknownEnumValue messageWithUnknownEnums =
        TestUnknownEnumValue.parseFrom(data);
    assertEquals(2, messageWithUnknownEnums.getInt32ToInt32Field().size());
    assertEquals(1, messageWithUnknownEnums.getInt32ToInt32Field().get(1).intValue());
    assertEquals(54321, messageWithUnknownEnums.getInt32ToInt32Field().get(2).intValue());
  }


  public void testRequiredMessage() throws Exception {
    TestMap.Builder builder = TestMap.newBuilder();
    builder.getMutableRequiredMessageMap().put(0,
        MessageWithRequiredFields.newBuilder().buildPartial());
    TestMap message = builder.buildPartial();
    assertFalse(message.isInitialized());

    builder.getMutableRequiredMessageMap().put(0,
        MessageWithRequiredFields.newBuilder().setValue(1).build());
    message = builder.build();
    assertTrue(message.isInitialized());
  }

  public void testRecursiveMap() throws Exception {
    TestRecursiveMap.Builder builder = TestRecursiveMap.newBuilder();
    builder.getMutableRecursiveMapField().put(
        1, TestRecursiveMap.newBuilder().setValue(2).build());
    builder.getMutableRecursiveMapField().put(
        3, TestRecursiveMap.newBuilder().setValue(4).build());
    ByteString data = builder.build().toByteString();

    TestRecursiveMap message = TestRecursiveMap.parseFrom(data);
    assertEquals(2, message.getRecursiveMapField().get(1).getValue());
    assertEquals(4, message.getRecursiveMapField().get(3).getValue());
  }

  public void testIterationOrder() throws Exception {
    TestMap.Builder builder = TestMap.newBuilder();
    setMapValues(builder);
    TestMap message = builder.build();

    assertEquals(Arrays.asList("1", "2", "3"),
        new ArrayList<String>(message.getStringToInt32Field().keySet()));
  }

  // Regression test for b/20494788
  public void testMapInitializationOrder() throws Exception {
    assertEquals("RedactAllTypes", map_test.RedactAllTypes
        .getDefaultInstance().getDescriptorForType().getName());

    map_test.Message1.Builder builder =
        map_test.Message1.newBuilder();
    builder.getMutableMapField().put("key", true);
    map_test.Message1 message = builder.build();
    Message mapEntry = (Message) message.getRepeatedField(
        message.getDescriptorForType().findFieldByName("map_field"), 0);
    assertEquals(2, mapEntry.getAllFields().size());
  }
  
  private static <K, V> Map<K, V> newMap(K key1, V value1) {
    Map<K, V> map = new HashMap<K, V>();
    map.put(key1, value1);
    return map;
  }
  
  private static <K, V> Map<K, V> newMap(K key1, V value1, K key2, V value2) {
    Map<K, V> map = new HashMap<K, V>();
    map.put(key1, value1);
    map.put(key2, value2);
    return map;
  }
}

