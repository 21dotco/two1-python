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

#import "GPBUtilities_PackagePrivate.h"

#import <objc/runtime.h>

#import "GPBArray_PackagePrivate.h"
#import "GPBDescriptor_PackagePrivate.h"
#import "GPBDictionary_PackagePrivate.h"
#import "GPBExtensionField.h"
#import "GPBField.h"
#import "GPBMessage_PackagePrivate.h"
#import "GPBUnknownFieldSet.h"

static void AppendTextFormatForMessage(GPBMessage *message,
                                       NSMutableString *toStr,
                                       NSString *lineIndent);

NSData *GPBEmptyNSData(void) {
  static dispatch_once_t onceToken;
  static NSData *defaultNSData = nil;
  dispatch_once(&onceToken, ^{
    defaultNSData = [[NSData alloc] init];
  });
  return defaultNSData;
}

BOOL GPBMessageHasFieldNumberSet(GPBMessage *self, uint32_t fieldNumber) {
  GPBDescriptor *descriptor = [self descriptor];
  GPBFieldDescriptor *field = [descriptor fieldWithNumber:fieldNumber];
  return GPBMessageHasFieldSet(self, field);
}

BOOL GPBMessageHasFieldSet(GPBMessage *self, GPBFieldDescriptor *field) {
  if (self == nil || field == nil) return NO;

  // Repeated/Map don't use the bit, they check the count.
  if (GPBFieldIsMapOrArray(field)) {
    // Array/map type doesn't matter, since GPB*Array/NSArray and
    // GPB*Dictionary/NSDictionary all support -count;
    NSArray *arrayOrMap = GPBGetObjectIvarWithFieldNoAutocreate(self, field);
    return (arrayOrMap.count > 0);
  } else {
    return GPBGetHasIvarField(self, field);
  }
}

void GPBClearMessageField(GPBMessage *self, GPBFieldDescriptor *field) {
  // If not set, nothing to do.
  if (!GPBGetHasIvarField(self, field)) {
    return;
  }

  if (GPBFieldStoresObject(field)) {
    // Object types are handled slightly differently, they need to be released.
    uint8_t *storage = (uint8_t *)self->messageStorage_;
    id *typePtr = (id *)&storage[field->description_->offset];
    [*typePtr release];
    *typePtr = nil;
  } else {
    // POD types just need to clear the has bit as the Get* method will
    // fetch the default when needed.
  }
  GPBSetHasIvarField(self, field, NO);
}

BOOL GPBGetHasIvar(GPBMessage *self, int32_t idx, uint32_t fieldNumber) {
  NSCAssert(self->messageStorage_ != NULL,
            @"%@: All messages should have storage (from init)",
            [self class]);
  if (idx < 0) {
    NSCAssert(fieldNumber != 0, @"Invalid field number.");
    BOOL hasIvar = (self->messageStorage_->_has_storage_[-idx] == fieldNumber);
    return hasIvar;
  } else {
    NSCAssert(idx != GPBNoHasBit, @"Invalid has bit.");
    uint32_t byteIndex = idx / 32;
    uint32_t bitMask = (1 << (idx % 32));
    BOOL hasIvar =
        (self->messageStorage_->_has_storage_[byteIndex] & bitMask) ? YES : NO;
    return hasIvar;
  }
}

uint32_t GPBGetHasOneof(GPBMessage *self, int32_t idx) {
  NSCAssert(idx < 0, @"%@: invalid index (%d) for oneof.",
            [self class], idx);
  uint32_t result = self->messageStorage_->_has_storage_[-idx];
  return result;
}

void GPBSetHasIvar(GPBMessage *self, int32_t idx, uint32_t fieldNumber,
                   BOOL value) {
  if (idx < 0) {
    NSCAssert(fieldNumber != 0, @"Invalid field number.");
    uint32_t *has_storage = self->messageStorage_->_has_storage_;
    has_storage[-idx] = (value ? fieldNumber : 0);
  } else {
    NSCAssert(idx != GPBNoHasBit, @"Invalid has bit.");
    uint32_t *has_storage = self->messageStorage_->_has_storage_;
    uint32_t byte = idx / 32;
    uint32_t bitMask = (1 << (idx % 32));
    if (value) {
      has_storage[byte] |= bitMask;
    } else {
      has_storage[byte] &= ~bitMask;
    }
  }
}

void GPBMaybeClearOneof(GPBMessage *self, GPBOneofDescriptor *oneof,
                        uint32_t fieldNumberNotToClear) {
  int32_t hasIndex = oneof->oneofDescription_->index;
  uint32_t fieldNumberSet = GPBGetHasOneof(self, hasIndex);
  if ((fieldNumberSet == fieldNumberNotToClear) || (fieldNumberSet == 0)) {
    // Do nothing/nothing set in the oneof.
    return;
  }

  // Like GPBClearMessageField(), free the memory if an objecttype is set,
  // pod types don't need to do anything.
  GPBFieldDescriptor *fieldSet = [oneof fieldWithNumber:fieldNumberSet];
  NSCAssert(fieldSet,
            @"%@: oneof set to something (%u) not in the oneof?",
            [self class], fieldNumberSet);
  if (fieldSet && GPBFieldStoresObject(fieldSet)) {
    uint8_t *storage = (uint8_t *)self->messageStorage_;
    id *typePtr = (id *)&storage[fieldSet->description_->offset];
    [*typePtr release];
    *typePtr = nil;
  }

  // Set to nothing stored in the oneof.
  // (field number doesn't matter since setting to nothing).
  GPBSetHasIvar(self, hasIndex, 1, NO);
}

#pragma mark - IVar accessors

//%PDDM-DEFINE IVAR_POD_ACCESSORS_DEFN(NAME, TYPE)
//%TYPE GPBGet##NAME##IvarWithField(GPBMessage *self,
//% TYPE$S     NAME$S               GPBFieldDescriptor *field) {
//%  if (GPBGetHasIvarField(self, field)) {
//%    uint8_t *storage = (uint8_t *)self->messageStorage_;
//%    TYPE *typePtr = (TYPE *)&storage[field->description_->offset];
//%    return *typePtr;
//%  } else {
//%    return field.defaultValue.value##NAME;
//%  }
//%}
//%
//%// Only exists for public api, no core code should use this.
//%void GPBSet##NAME##IvarWithField(GPBMessage *self,
//%            NAME$S             GPBFieldDescriptor *field,
//%            NAME$S             TYPE value) {
//%  if (self == nil || field == nil) return;
//%  GPBFileSyntax syntax = [self descriptor].file.syntax;
//%  GPBSet##NAME##IvarWithFieldInternal(self, field, value, syntax);
//%}
//%
//%void GPBSet##NAME##IvarWithFieldInternal(GPBMessage *self,
//%            NAME$S                     GPBFieldDescriptor *field,
//%            NAME$S                     TYPE value,
//%            NAME$S                     GPBFileSyntax syntax) {
//%  GPBOneofDescriptor *oneof = field->containingOneof_;
//%  if (oneof) {
//%    GPBMaybeClearOneof(self, oneof, GPBFieldNumber(field));
//%  }
//%  NSCAssert(self->messageStorage_ != NULL,
//%            @"%@: All messages should have storage (from init)",
//%            [self class]);
//%#if defined(__clang_analyzer__)
//%  if (self->messageStorage_ == NULL) return;
//%#endif
//%  uint8_t *storage = (uint8_t *)self->messageStorage_;
//%  TYPE *typePtr = (TYPE *)&storage[field->description_->offset];
//%  *typePtr = value;
//%  // proto2: any value counts as having been set; proto3, it
//%  // has to be a non zero value.
//%  BOOL hasValue =
//%    (syntax == GPBFileSyntaxProto2) || (value != (TYPE)0);
//%  GPBSetHasIvarField(self, field, hasValue);
//%  GPBBecomeVisibleToAutocreator(self);
//%}
//%
//%PDDM-DEFINE IVAR_ALIAS_DEFN(NAME, ALIAS_NAME, TYPE, ALIAS_TYPE)
//%// Only exists for public api, no core code should use this.
//%TYPE GPBGet##NAME##IvarWithField(GPBMessage *self,
//% TYPE$S     NAME$S               GPBFieldDescriptor *field) {
//%  return (TYPE)GPBGet##ALIAS_NAME##IvarWithField(self, field);
//%}
//%
//%// Only exists for public api, no core code should use this.
//%void GPBSet##NAME##IvarWithField(GPBMessage *self,
//%            NAME$S             GPBFieldDescriptor *field,
//%            NAME$S             TYPE value) {
//%  GPBSet##ALIAS_NAME##IvarWithField(self, field, (ALIAS_TYPE)value);
//%}
//%

// Object types are handled slightly differently, they need to be released
// and retained.

void GPBSetAutocreatedRetainedObjectIvarWithField(
    GPBMessage *self, GPBFieldDescriptor *field,
    id __attribute__((ns_consumed)) value) {
  uint8_t *storage = (uint8_t *)self->messageStorage_;
  id *typePtr = (id *)&storage[field->description_->offset];
  NSCAssert(*typePtr == NULL, @"Can't set autocreated object more than once.");
  *typePtr = value;
}

void GPBClearAutocreatedMessageIvarWithField(GPBMessage *self,
                                             GPBFieldDescriptor *field) {
  if (GPBGetHasIvarField(self, field)) {
    return;
  }
  uint8_t *storage = (uint8_t *)self->messageStorage_;
  id *typePtr = (id *)&storage[field->description_->offset];
  GPBMessage *oldValue = *typePtr;
  *typePtr = NULL;
  GPBClearMessageAutocreator(oldValue);
  [oldValue release];
}

// This exists only for briging some aliased types, nothing else should use it.
GPB_INLINE void GPBSetObjectIvarWithField(GPBMessage *self,
                                          GPBFieldDescriptor *field, id value) {
  if (self == nil || field == nil) return;
  GPBFileSyntax syntax = [self descriptor].file.syntax;
  GPBSetRetainedObjectIvarWithFieldInternal(self, field, [value retain],
                                            syntax);
}

void GPBSetObjectIvarWithFieldInternal(GPBMessage *self,
                                       GPBFieldDescriptor *field, id value,
                                       GPBFileSyntax syntax) {
  GPBSetRetainedObjectIvarWithFieldInternal(self, field, [value retain],
                                            syntax);
}

void GPBSetRetainedObjectIvarWithFieldInternal(GPBMessage *self,
                                               GPBFieldDescriptor *field,
                                               id value, GPBFileSyntax syntax) {
  NSCAssert(self->messageStorage_ != NULL,
            @"%@: All messages should have storage (from init)",
            [self class]);
#if defined(__clang_analyzer__)
  if (self->messageStorage_ == NULL) return;
#endif
  GPBType fieldType = GPBGetFieldType(field);
  BOOL isMapOrArray = GPBFieldIsMapOrArray(field);
  BOOL fieldIsMessage = GPBTypeIsMessage(fieldType);
#ifdef DEBUG
  if (value == nil && !isMapOrArray && !fieldIsMessage &&
      field.hasDefaultValue) {
    // Setting a message to nil is an obvious way to "clear" the value
    // as there is no way to set a non-empty default value for messages.
    //
    // For Strings and Bytes that have default values set it is not clear what
    // should be done when their value is set to nil. Is the intention just to
    // clear the set value and reset to default, or is the intention to set the
    // value to the empty string/data? Arguments can be made for both cases.
    // 'nil' has been abused as a replacement for an empty string/data in ObjC.
    // We decided to be consistent with all "object" types and clear the has
    // field, and fall back on the default value. The warning below will only
    // appear in debug, but the could should be changed so the intention is
    // clear.
    NSString *hasSel = NSStringFromSelector(field->hasSel_);
    NSString *propName = field.name;
    NSString *className = self.descriptor.name;
    NSLog(@"warning: '%@.%@ = nil;' is not clearly defined for fields with "
          @"default values. Please use '%@.%@ = %@' if you want to set it to "
          @"empty, or call '%@.%@ = NO' to reset it to it's default value of "
          @"'%@'. Defaulting to resetting default value.",
          className, propName, className, propName,
          (fieldType == GPBTypeString) ? @"@\"\"" : @"GPBEmptyNSData()",
          className, hasSel, field.defaultValue.valueString);
    // Note: valueString, depending on the type, it could easily be
    // valueData/valueMessage.
  }
#endif  // DEBUG
  if (!isMapOrArray) {
    // Non repeated/map can be in an oneof, clear any existing value from the
    // oneof.
    GPBOneofDescriptor *oneof = field->containingOneof_;
    if (oneof) {
      GPBMaybeClearOneof(self, oneof, GPBFieldNumber(field));
    }
    // Clear "has" if they are being set to nil.
    BOOL setHasValue = (value != nil);
    // Under proto3, Data & String fields get cleared by resetting them to their
    // default (empty) values, so if they are set to something of length zero,
    // they are being cleared.
    if ((syntax == GPBFileSyntaxProto3) && !fieldIsMessage &&
        ([value length] == 0)) {
      setHasValue = NO;
      value = nil;
    }
    GPBSetHasIvarField(self, field, setHasValue);
  }
  uint8_t *storage = (uint8_t *)self->messageStorage_;
  id *typePtr = (id *)&storage[field->description_->offset];

  id oldValue = *typePtr;

  *typePtr = value;

  if (oldValue) {
    if (isMapOrArray) {
      if (field.fieldType == GPBFieldTypeRepeated) {
        // If the old array was autocreated by us, then clear it.
        if (GPBTypeIsObject(fieldType)) {
          GPBAutocreatedArray *autoArray = oldValue;
          if (autoArray->_autocreator == self) {
            autoArray->_autocreator = nil;
          }
        } else {
          // Type doesn't matter, it is a GPB*Array.
          GPBInt32Array *gpbArray = oldValue;
          if (gpbArray->_autocreator == self) {
            gpbArray->_autocreator = nil;
          }
        }
      } else { // GPBFieldTypeMap
        // If the old map was autocreated by us, then clear it.
        if ((field.mapKeyType == GPBTypeString) &&
            GPBTypeIsObject(fieldType)) {
          GPBAutocreatedDictionary *autoDict = oldValue;
          if (autoDict->_autocreator == self) {
            autoDict->_autocreator = nil;
          }
        } else {
          // Type doesn't matter, it is a GPB*Dictionary.
          GPBInt32Int32Dictionary *gpbDict = oldValue;
          if (gpbDict->_autocreator == self) {
            gpbDict->_autocreator = nil;
          }
        }
      }
    } else if (fieldIsMessage) {
      // If the old message value was autocreated by us, then clear it.
      GPBMessage *oldMessageValue = oldValue;
      if (GPBWasMessageAutocreatedBy(oldMessageValue, self)) {
        GPBClearMessageAutocreator(oldMessageValue);
      }
    }
    [oldValue release];
  }

  GPBBecomeVisibleToAutocreator(self);
}

id GPBGetObjectIvarWithFieldNoAutocreate(GPBMessage *self,
                                         GPBFieldDescriptor *field) {
  if (self->messageStorage_ == nil) {
    return nil;
  }
  uint8_t *storage = (uint8_t *)self->messageStorage_;
  id *typePtr = (id *)&storage[field->description_->offset];
  return *typePtr;
}

id GPBGetObjectIvarWithField(GPBMessage *self, GPBFieldDescriptor *field) {
  NSCAssert(!GPBFieldIsMapOrArray(field), @"Shouldn't get here");
  if (GPBGetHasIvarField(self, field)) {
    uint8_t *storage = (uint8_t *)self->messageStorage_;
    id *typePtr = (id *)&storage[field->description_->offset];
    return *typePtr;
  }
  // Not set...

  // Non messages (string/data), get their default.
  if (!GPBFieldTypeIsMessage(field)) {
    return field.defaultValue.valueMessage;
  }

  OSSpinLockLock(&self->readOnlyMutex_);
  GPBMessage *result = GPBGetObjectIvarWithFieldNoAutocreate(self, field);
  if (!result) {
    // For non repeated messages, create the object, set it and return it.
    // This object will not initially be visible via GPBGetHasIvar, so
    // we save its creator so it can become visible if it's mutated later.
    result = GPBCreateMessageWithAutocreator(field.msgClass, self, field);
    GPBSetAutocreatedRetainedObjectIvarWithField(self, field, result);
  }
  OSSpinLockUnlock(&self->readOnlyMutex_);
  return result;
}

// Only exists for public api, no core code should use this.
int32_t GPBGetEnumIvarWithField(GPBMessage *self, GPBFieldDescriptor *field) {
  GPBFileSyntax syntax = [self descriptor].file.syntax;
  return GPBGetEnumIvarWithFieldInternal(self, field, syntax);
}

int32_t GPBGetEnumIvarWithFieldInternal(GPBMessage *self,
                                        GPBFieldDescriptor *field,
                                        GPBFileSyntax syntax) {
  int32_t result = GPBGetInt32IvarWithField(self, field);
  // If this is presevering unknown enums, make sure the value is
  // valid before returning it.
  if (GPBHasPreservingUnknownEnumSemantics(syntax) &&
      ![field isValidEnumValue:result]) {
    result = kGPBUnrecognizedEnumeratorValue;
  }
  return result;
}

// Only exists for public api, no core code should use this.
void GPBSetEnumIvarWithField(GPBMessage *self, GPBFieldDescriptor *field,
                             int32_t value) {
  GPBFileSyntax syntax = [self descriptor].file.syntax;
  GPBSetInt32IvarWithFieldInternal(self, field, value, syntax);
}

void GPBSetEnumIvarWithFieldInternal(GPBMessage *self,
                                     GPBFieldDescriptor *field, int32_t value,
                                     GPBFileSyntax syntax) {
  // Don't allow in unknown values.  Proto3 can use the Raw method.
  if (![field isValidEnumValue:value]) {
    [NSException raise:NSInvalidArgumentException
                format:@"%@.%@: Attempt to set an unknown enum value (%d)",
                       [self class], field.name, value];
  }
  GPBSetInt32IvarWithFieldInternal(self, field, value, syntax);
}

//%PDDM-EXPAND IVAR_POD_ACCESSORS_DEFN(Bool, BOOL)
// This block of code is generated, do not edit it directly.

BOOL GPBGetBoolIvarWithField(GPBMessage *self,
                             GPBFieldDescriptor *field) {
  if (GPBGetHasIvarField(self, field)) {
    uint8_t *storage = (uint8_t *)self->messageStorage_;
    BOOL *typePtr = (BOOL *)&storage[field->description_->offset];
    return *typePtr;
  } else {
    return field.defaultValue.valueBool;
  }
}

// Only exists for public api, no core code should use this.
void GPBSetBoolIvarWithField(GPBMessage *self,
                             GPBFieldDescriptor *field,
                             BOOL value) {
  if (self == nil || field == nil) return;
  GPBFileSyntax syntax = [self descriptor].file.syntax;
  GPBSetBoolIvarWithFieldInternal(self, field, value, syntax);
}

void GPBSetBoolIvarWithFieldInternal(GPBMessage *self,
                                     GPBFieldDescriptor *field,
                                     BOOL value,
                                     GPBFileSyntax syntax) {
  GPBOneofDescriptor *oneof = field->containingOneof_;
  if (oneof) {
    GPBMaybeClearOneof(self, oneof, GPBFieldNumber(field));
  }
  NSCAssert(self->messageStorage_ != NULL,
            @"%@: All messages should have storage (from init)",
            [self class]);
#if defined(__clang_analyzer__)
  if (self->messageStorage_ == NULL) return;
#endif
  uint8_t *storage = (uint8_t *)self->messageStorage_;
  BOOL *typePtr = (BOOL *)&storage[field->description_->offset];
  *typePtr = value;
  // proto2: any value counts as having been set; proto3, it
  // has to be a non zero value.
  BOOL hasValue =
    (syntax == GPBFileSyntaxProto2) || (value != (BOOL)0);
  GPBSetHasIvarField(self, field, hasValue);
  GPBBecomeVisibleToAutocreator(self);
}

//%PDDM-EXPAND IVAR_POD_ACCESSORS_DEFN(Int32, int32_t)
// This block of code is generated, do not edit it directly.

int32_t GPBGetInt32IvarWithField(GPBMessage *self,
                                 GPBFieldDescriptor *field) {
  if (GPBGetHasIvarField(self, field)) {
    uint8_t *storage = (uint8_t *)self->messageStorage_;
    int32_t *typePtr = (int32_t *)&storage[field->description_->offset];
    return *typePtr;
  } else {
    return field.defaultValue.valueInt32;
  }
}

// Only exists for public api, no core code should use this.
void GPBSetInt32IvarWithField(GPBMessage *self,
                              GPBFieldDescriptor *field,
                              int32_t value) {
  if (self == nil || field == nil) return;
  GPBFileSyntax syntax = [self descriptor].file.syntax;
  GPBSetInt32IvarWithFieldInternal(self, field, value, syntax);
}

void GPBSetInt32IvarWithFieldInternal(GPBMessage *self,
                                      GPBFieldDescriptor *field,
                                      int32_t value,
                                      GPBFileSyntax syntax) {
  GPBOneofDescriptor *oneof = field->containingOneof_;
  if (oneof) {
    GPBMaybeClearOneof(self, oneof, GPBFieldNumber(field));
  }
  NSCAssert(self->messageStorage_ != NULL,
            @"%@: All messages should have storage (from init)",
            [self class]);
#if defined(__clang_analyzer__)
  if (self->messageStorage_ == NULL) return;
#endif
  uint8_t *storage = (uint8_t *)self->messageStorage_;
  int32_t *typePtr = (int32_t *)&storage[field->description_->offset];
  *typePtr = value;
  // proto2: any value counts as having been set; proto3, it
  // has to be a non zero value.
  BOOL hasValue =
    (syntax == GPBFileSyntaxProto2) || (value != (int32_t)0);
  GPBSetHasIvarField(self, field, hasValue);
  GPBBecomeVisibleToAutocreator(self);
}

//%PDDM-EXPAND IVAR_POD_ACCESSORS_DEFN(UInt32, uint32_t)
// This block of code is generated, do not edit it directly.

uint32_t GPBGetUInt32IvarWithField(GPBMessage *self,
                                   GPBFieldDescriptor *field) {
  if (GPBGetHasIvarField(self, field)) {
    uint8_t *storage = (uint8_t *)self->messageStorage_;
    uint32_t *typePtr = (uint32_t *)&storage[field->description_->offset];
    return *typePtr;
  } else {
    return field.defaultValue.valueUInt32;
  }
}

// Only exists for public api, no core code should use this.
void GPBSetUInt32IvarWithField(GPBMessage *self,
                               GPBFieldDescriptor *field,
                               uint32_t value) {
  if (self == nil || field == nil) return;
  GPBFileSyntax syntax = [self descriptor].file.syntax;
  GPBSetUInt32IvarWithFieldInternal(self, field, value, syntax);
}

void GPBSetUInt32IvarWithFieldInternal(GPBMessage *self,
                                       GPBFieldDescriptor *field,
                                       uint32_t value,
                                       GPBFileSyntax syntax) {
  GPBOneofDescriptor *oneof = field->containingOneof_;
  if (oneof) {
    GPBMaybeClearOneof(self, oneof, GPBFieldNumber(field));
  }
  NSCAssert(self->messageStorage_ != NULL,
            @"%@: All messages should have storage (from init)",
            [self class]);
#if defined(__clang_analyzer__)
  if (self->messageStorage_ == NULL) return;
#endif
  uint8_t *storage = (uint8_t *)self->messageStorage_;
  uint32_t *typePtr = (uint32_t *)&storage[field->description_->offset];
  *typePtr = value;
  // proto2: any value counts as having been set; proto3, it
  // has to be a non zero value.
  BOOL hasValue =
    (syntax == GPBFileSyntaxProto2) || (value != (uint32_t)0);
  GPBSetHasIvarField(self, field, hasValue);
  GPBBecomeVisibleToAutocreator(self);
}

//%PDDM-EXPAND IVAR_POD_ACCESSORS_DEFN(Int64, int64_t)
// This block of code is generated, do not edit it directly.

int64_t GPBGetInt64IvarWithField(GPBMessage *self,
                                 GPBFieldDescriptor *field) {
  if (GPBGetHasIvarField(self, field)) {
    uint8_t *storage = (uint8_t *)self->messageStorage_;
    int64_t *typePtr = (int64_t *)&storage[field->description_->offset];
    return *typePtr;
  } else {
    return field.defaultValue.valueInt64;
  }
}

// Only exists for public api, no core code should use this.
void GPBSetInt64IvarWithField(GPBMessage *self,
                              GPBFieldDescriptor *field,
                              int64_t value) {
  if (self == nil || field == nil) return;
  GPBFileSyntax syntax = [self descriptor].file.syntax;
  GPBSetInt64IvarWithFieldInternal(self, field, value, syntax);
}

void GPBSetInt64IvarWithFieldInternal(GPBMessage *self,
                                      GPBFieldDescriptor *field,
                                      int64_t value,
                                      GPBFileSyntax syntax) {
  GPBOneofDescriptor *oneof = field->containingOneof_;
  if (oneof) {
    GPBMaybeClearOneof(self, oneof, GPBFieldNumber(field));
  }
  NSCAssert(self->messageStorage_ != NULL,
            @"%@: All messages should have storage (from init)",
            [self class]);
#if defined(__clang_analyzer__)
  if (self->messageStorage_ == NULL) return;
#endif
  uint8_t *storage = (uint8_t *)self->messageStorage_;
  int64_t *typePtr = (int64_t *)&storage[field->description_->offset];
  *typePtr = value;
  // proto2: any value counts as having been set; proto3, it
  // has to be a non zero value.
  BOOL hasValue =
    (syntax == GPBFileSyntaxProto2) || (value != (int64_t)0);
  GPBSetHasIvarField(self, field, hasValue);
  GPBBecomeVisibleToAutocreator(self);
}

//%PDDM-EXPAND IVAR_POD_ACCESSORS_DEFN(UInt64, uint64_t)
// This block of code is generated, do not edit it directly.

uint64_t GPBGetUInt64IvarWithField(GPBMessage *self,
                                   GPBFieldDescriptor *field) {
  if (GPBGetHasIvarField(self, field)) {
    uint8_t *storage = (uint8_t *)self->messageStorage_;
    uint64_t *typePtr = (uint64_t *)&storage[field->description_->offset];
    return *typePtr;
  } else {
    return field.defaultValue.valueUInt64;
  }
}

// Only exists for public api, no core code should use this.
void GPBSetUInt64IvarWithField(GPBMessage *self,
                               GPBFieldDescriptor *field,
                               uint64_t value) {
  if (self == nil || field == nil) return;
  GPBFileSyntax syntax = [self descriptor].file.syntax;
  GPBSetUInt64IvarWithFieldInternal(self, field, value, syntax);
}

void GPBSetUInt64IvarWithFieldInternal(GPBMessage *self,
                                       GPBFieldDescriptor *field,
                                       uint64_t value,
                                       GPBFileSyntax syntax) {
  GPBOneofDescriptor *oneof = field->containingOneof_;
  if (oneof) {
    GPBMaybeClearOneof(self, oneof, GPBFieldNumber(field));
  }
  NSCAssert(self->messageStorage_ != NULL,
            @"%@: All messages should have storage (from init)",
            [self class]);
#if defined(__clang_analyzer__)
  if (self->messageStorage_ == NULL) return;
#endif
  uint8_t *storage = (uint8_t *)self->messageStorage_;
  uint64_t *typePtr = (uint64_t *)&storage[field->description_->offset];
  *typePtr = value;
  // proto2: any value counts as having been set; proto3, it
  // has to be a non zero value.
  BOOL hasValue =
    (syntax == GPBFileSyntaxProto2) || (value != (uint64_t)0);
  GPBSetHasIvarField(self, field, hasValue);
  GPBBecomeVisibleToAutocreator(self);
}

//%PDDM-EXPAND IVAR_POD_ACCESSORS_DEFN(Float, float)
// This block of code is generated, do not edit it directly.

float GPBGetFloatIvarWithField(GPBMessage *self,
                               GPBFieldDescriptor *field) {
  if (GPBGetHasIvarField(self, field)) {
    uint8_t *storage = (uint8_t *)self->messageStorage_;
    float *typePtr = (float *)&storage[field->description_->offset];
    return *typePtr;
  } else {
    return field.defaultValue.valueFloat;
  }
}

// Only exists for public api, no core code should use this.
void GPBSetFloatIvarWithField(GPBMessage *self,
                              GPBFieldDescriptor *field,
                              float value) {
  if (self == nil || field == nil) return;
  GPBFileSyntax syntax = [self descriptor].file.syntax;
  GPBSetFloatIvarWithFieldInternal(self, field, value, syntax);
}

void GPBSetFloatIvarWithFieldInternal(GPBMessage *self,
                                      GPBFieldDescriptor *field,
                                      float value,
                                      GPBFileSyntax syntax) {
  GPBOneofDescriptor *oneof = field->containingOneof_;
  if (oneof) {
    GPBMaybeClearOneof(self, oneof, GPBFieldNumber(field));
  }
  NSCAssert(self->messageStorage_ != NULL,
            @"%@: All messages should have storage (from init)",
            [self class]);
#if defined(__clang_analyzer__)
  if (self->messageStorage_ == NULL) return;
#endif
  uint8_t *storage = (uint8_t *)self->messageStorage_;
  float *typePtr = (float *)&storage[field->description_->offset];
  *typePtr = value;
  // proto2: any value counts as having been set; proto3, it
  // has to be a non zero value.
  BOOL hasValue =
    (syntax == GPBFileSyntaxProto2) || (value != (float)0);
  GPBSetHasIvarField(self, field, hasValue);
  GPBBecomeVisibleToAutocreator(self);
}

//%PDDM-EXPAND IVAR_POD_ACCESSORS_DEFN(Double, double)
// This block of code is generated, do not edit it directly.

double GPBGetDoubleIvarWithField(GPBMessage *self,
                                 GPBFieldDescriptor *field) {
  if (GPBGetHasIvarField(self, field)) {
    uint8_t *storage = (uint8_t *)self->messageStorage_;
    double *typePtr = (double *)&storage[field->description_->offset];
    return *typePtr;
  } else {
    return field.defaultValue.valueDouble;
  }
}

// Only exists for public api, no core code should use this.
void GPBSetDoubleIvarWithField(GPBMessage *self,
                               GPBFieldDescriptor *field,
                               double value) {
  if (self == nil || field == nil) return;
  GPBFileSyntax syntax = [self descriptor].file.syntax;
  GPBSetDoubleIvarWithFieldInternal(self, field, value, syntax);
}

void GPBSetDoubleIvarWithFieldInternal(GPBMessage *self,
                                       GPBFieldDescriptor *field,
                                       double value,
                                       GPBFileSyntax syntax) {
  GPBOneofDescriptor *oneof = field->containingOneof_;
  if (oneof) {
    GPBMaybeClearOneof(self, oneof, GPBFieldNumber(field));
  }
  NSCAssert(self->messageStorage_ != NULL,
            @"%@: All messages should have storage (from init)",
            [self class]);
#if defined(__clang_analyzer__)
  if (self->messageStorage_ == NULL) return;
#endif
  uint8_t *storage = (uint8_t *)self->messageStorage_;
  double *typePtr = (double *)&storage[field->description_->offset];
  *typePtr = value;
  // proto2: any value counts as having been set; proto3, it
  // has to be a non zero value.
  BOOL hasValue =
    (syntax == GPBFileSyntaxProto2) || (value != (double)0);
  GPBSetHasIvarField(self, field, hasValue);
  GPBBecomeVisibleToAutocreator(self);
}

//%PDDM-EXPAND-END (7 expansions)

// Aliases are function calls that are virtually the same.

//%PDDM-EXPAND IVAR_ALIAS_DEFN(SInt32, Int32, int32_t, int32_t)
// This block of code is generated, do not edit it directly.

// Only exists for public api, no core code should use this.
int32_t GPBGetSInt32IvarWithField(GPBMessage *self,
                                  GPBFieldDescriptor *field) {
  return (int32_t)GPBGetInt32IvarWithField(self, field);
}

// Only exists for public api, no core code should use this.
void GPBSetSInt32IvarWithField(GPBMessage *self,
                               GPBFieldDescriptor *field,
                               int32_t value) {
  GPBSetInt32IvarWithField(self, field, (int32_t)value);
}

//%PDDM-EXPAND IVAR_ALIAS_DEFN(SFixed32, Int32, int32_t, int32_t)
// This block of code is generated, do not edit it directly.

// Only exists for public api, no core code should use this.
int32_t GPBGetSFixed32IvarWithField(GPBMessage *self,
                                    GPBFieldDescriptor *field) {
  return (int32_t)GPBGetInt32IvarWithField(self, field);
}

// Only exists for public api, no core code should use this.
void GPBSetSFixed32IvarWithField(GPBMessage *self,
                                 GPBFieldDescriptor *field,
                                 int32_t value) {
  GPBSetInt32IvarWithField(self, field, (int32_t)value);
}

//%PDDM-EXPAND IVAR_ALIAS_DEFN(Fixed32, UInt32, uint32_t, uint32_t)
// This block of code is generated, do not edit it directly.

// Only exists for public api, no core code should use this.
uint32_t GPBGetFixed32IvarWithField(GPBMessage *self,
                                    GPBFieldDescriptor *field) {
  return (uint32_t)GPBGetUInt32IvarWithField(self, field);
}

// Only exists for public api, no core code should use this.
void GPBSetFixed32IvarWithField(GPBMessage *self,
                                GPBFieldDescriptor *field,
                                uint32_t value) {
  GPBSetUInt32IvarWithField(self, field, (uint32_t)value);
}

//%PDDM-EXPAND IVAR_ALIAS_DEFN(SInt64, Int64, int64_t, int64_t)
// This block of code is generated, do not edit it directly.

// Only exists for public api, no core code should use this.
int64_t GPBGetSInt64IvarWithField(GPBMessage *self,
                                  GPBFieldDescriptor *field) {
  return (int64_t)GPBGetInt64IvarWithField(self, field);
}

// Only exists for public api, no core code should use this.
void GPBSetSInt64IvarWithField(GPBMessage *self,
                               GPBFieldDescriptor *field,
                               int64_t value) {
  GPBSetInt64IvarWithField(self, field, (int64_t)value);
}

//%PDDM-EXPAND IVAR_ALIAS_DEFN(SFixed64, Int64, int64_t, int64_t)
// This block of code is generated, do not edit it directly.

// Only exists for public api, no core code should use this.
int64_t GPBGetSFixed64IvarWithField(GPBMessage *self,
                                    GPBFieldDescriptor *field) {
  return (int64_t)GPBGetInt64IvarWithField(self, field);
}

// Only exists for public api, no core code should use this.
void GPBSetSFixed64IvarWithField(GPBMessage *self,
                                 GPBFieldDescriptor *field,
                                 int64_t value) {
  GPBSetInt64IvarWithField(self, field, (int64_t)value);
}

//%PDDM-EXPAND IVAR_ALIAS_DEFN(Fixed64, UInt64, uint64_t, uint64_t)
// This block of code is generated, do not edit it directly.

// Only exists for public api, no core code should use this.
uint64_t GPBGetFixed64IvarWithField(GPBMessage *self,
                                    GPBFieldDescriptor *field) {
  return (uint64_t)GPBGetUInt64IvarWithField(self, field);
}

// Only exists for public api, no core code should use this.
void GPBSetFixed64IvarWithField(GPBMessage *self,
                                GPBFieldDescriptor *field,
                                uint64_t value) {
  GPBSetUInt64IvarWithField(self, field, (uint64_t)value);
}

//%PDDM-EXPAND IVAR_ALIAS_DEFN(String, Object, NSString*, id)
// This block of code is generated, do not edit it directly.

// Only exists for public api, no core code should use this.
NSString* GPBGetStringIvarWithField(GPBMessage *self,
                                    GPBFieldDescriptor *field) {
  return (NSString*)GPBGetObjectIvarWithField(self, field);
}

// Only exists for public api, no core code should use this.
void GPBSetStringIvarWithField(GPBMessage *self,
                               GPBFieldDescriptor *field,
                               NSString* value) {
  GPBSetObjectIvarWithField(self, field, (id)value);
}

//%PDDM-EXPAND IVAR_ALIAS_DEFN(Data, Object, NSData*, id)
// This block of code is generated, do not edit it directly.

// Only exists for public api, no core code should use this.
NSData* GPBGetDataIvarWithField(GPBMessage *self,
                                GPBFieldDescriptor *field) {
  return (NSData*)GPBGetObjectIvarWithField(self, field);
}

// Only exists for public api, no core code should use this.
void GPBSetDataIvarWithField(GPBMessage *self,
                             GPBFieldDescriptor *field,
                             NSData* value) {
  GPBSetObjectIvarWithField(self, field, (id)value);
}

//%PDDM-EXPAND IVAR_ALIAS_DEFN(Message, Object, GPBMessage*, id)
// This block of code is generated, do not edit it directly.

// Only exists for public api, no core code should use this.
GPBMessage* GPBGetMessageIvarWithField(GPBMessage *self,
                                       GPBFieldDescriptor *field) {
  return (GPBMessage*)GPBGetObjectIvarWithField(self, field);
}

// Only exists for public api, no core code should use this.
void GPBSetMessageIvarWithField(GPBMessage *self,
                                GPBFieldDescriptor *field,
                                GPBMessage* value) {
  GPBSetObjectIvarWithField(self, field, (id)value);
}

//%PDDM-EXPAND IVAR_ALIAS_DEFN(Group, Object, GPBMessage*, id)
// This block of code is generated, do not edit it directly.

// Only exists for public api, no core code should use this.
GPBMessage* GPBGetGroupIvarWithField(GPBMessage *self,
                                     GPBFieldDescriptor *field) {
  return (GPBMessage*)GPBGetObjectIvarWithField(self, field);
}

// Only exists for public api, no core code should use this.
void GPBSetGroupIvarWithField(GPBMessage *self,
                              GPBFieldDescriptor *field,
                              GPBMessage* value) {
  GPBSetObjectIvarWithField(self, field, (id)value);
}

//%PDDM-EXPAND-END (10 expansions)

#pragma mark - Misc Dynamic Runtime Utils

void GPBApplyFunctionsToMessageFields(GPBApplyFunctions *functions,
                                      GPBMessage *msg, void *context) {
  GPBDescriptor *descriptor = [[msg class] descriptor];
  for (GPBFieldDescriptor *field in descriptor->fields_) {
    BOOL wasGood;
    if (GPBFieldIsMapOrArray(field)) {
      wasGood = (*functions)[GPBApplyFunctionObject](field, context);
    } else {
      wasGood = GPBApplyFunctionsBasedOnField(field, functions, context);
    }
    if (!wasGood) {
      break;
    }
  }
}

BOOL GPBApplyFunctionsBasedOnField(GPBFieldDescriptor *field,
                                   GPBApplyFunctions *functions,
                                   void *context) {
  static const GPBApplyFunctionOrder typeMap[GPBTypeCount] = {
    GPBApplyFunctionBool,
    GPBApplyFunctionUInt32,
    GPBApplyFunctionInt32,
    GPBApplyFunctionFloat,
    GPBApplyFunctionUInt64,
    GPBApplyFunctionInt64,
    GPBApplyFunctionDouble,
    GPBApplyFunctionInt32,
    GPBApplyFunctionInt64,
    GPBApplyFunctionInt32,
    GPBApplyFunctionInt64,
    GPBApplyFunctionUInt32,
    GPBApplyFunctionUInt64,
    GPBApplyFunctionObject,
    GPBApplyFunctionObject,
    GPBApplyFunctionObject,
    GPBApplyFunctionObject,
    GPBApplyFunctionInt32
  };
  return (*functions)[typeMap[GPBGetFieldType(field)]](field, context);
}

void GPBApplyStrictFunctionsToMessageFields(GPBApplyStrictFunctions *functions,
                                            GPBMessage *msg, void *context) {
  GPBDescriptor *descriptor = [[msg class] descriptor];
  for (GPBFieldDescriptor *fieldDescriptor in descriptor->fields_) {
    GPBApplyFunction function = (*functions)[GPBGetFieldType(fieldDescriptor)];
    BOOL wasGood = function(fieldDescriptor, context);
    if (!wasGood) {
      break;
    }
  }
}

const char *GPBMessageEncodingForSelector(SEL selector, BOOL instanceSel) {
  Protocol *protocol =
      objc_getProtocol(GPBStringifySymbol(GPBMessageSignatureProtocol));
  struct objc_method_description description =
      protocol_getMethodDescription(protocol, selector, NO, instanceSel);
  return description.types;
}

#pragma mark - Text Format Support

static void AppendStringEscaped(NSString *toPrint, NSMutableString *destStr) {
  [destStr appendString:@"\""];
  NSUInteger len = [toPrint length];
  for (NSUInteger i = 0; i < len; ++i) {
    unichar aChar = [toPrint characterAtIndex:i];
    switch (aChar) {
      case '\n': [destStr appendString:@"\\n"];  break;
      case '\r': [destStr appendString:@"\\r"];  break;
      case '\t': [destStr appendString:@"\\t"];  break;
      case '\"': [destStr appendString:@"\\\""]; break;
      case '\'': [destStr appendString:@"\\\'"]; break;
      case '\\': [destStr appendString:@"\\\\"]; break;
      default:
        [destStr appendFormat:@"%C", aChar];
        break;
    }
  }
  [destStr appendString:@"\""];
}

static void AppendBufferAsString(NSData *buffer, NSMutableString *destStr) {
  const char *src = (const char *)[buffer bytes];
  size_t srcLen = [buffer length];
  [destStr appendString:@"\""];
  for (const char *srcEnd = src + srcLen; src < srcEnd; src++) {
    switch (*src) {
      case '\n': [destStr appendString:@"\\n"];  break;
      case '\r': [destStr appendString:@"\\r"];  break;
      case '\t': [destStr appendString:@"\\t"];  break;
      case '\"': [destStr appendString:@"\\\""]; break;
      case '\'': [destStr appendString:@"\\\'"]; break;
      case '\\': [destStr appendString:@"\\\\"]; break;
      default:
        if (isprint(*src)) {
          [destStr appendFormat:@"%c", *src];
        } else {
          // NOTE: doing hex means you have to worry about the letter after
          // the hex being another hex char and forcing that to be escaped, so
          // use octal to keep it simple.
          [destStr appendFormat:@"\\%03o", (uint8_t)(*src)];
        }
        break;
    }
  }
  [destStr appendString:@"\""];
}

static void AppendTextFormatForMapMessageField(
    id map, GPBFieldDescriptor *field, NSMutableString *toStr,
    NSString *lineIndent, NSString *fieldName, NSString *lineEnding) {
  GPBType keyType = field.mapKeyType;
  GPBType valueType = GPBGetFieldType(field);
  BOOL isMessageValue = GPBTypeIsMessage(valueType);

  NSString *msgStartFirst =
      [NSString stringWithFormat:@"%@%@ {%@\n", lineIndent, fieldName, lineEnding];
  NSString *msgStart =
      [NSString stringWithFormat:@"%@%@ {\n", lineIndent, fieldName];
  NSString *msgEnd = [NSString stringWithFormat:@"%@}\n", lineIndent];

  NSString *keyLine = [NSString stringWithFormat:@"%@  key: ", lineIndent];
  NSString *valueLine = [NSString stringWithFormat:@"%@  value%s ", lineIndent,
                                                   (isMessageValue ? "" : ":")];

  __block BOOL isFirst = YES;

  if ((keyType == GPBTypeString) && GPBTypeIsObject(valueType)) {
    // map is an NSDictionary.
    NSDictionary *dict = map;
    [dict enumerateKeysAndObjectsUsingBlock:^(NSString *key, id value, BOOL *stop) {
      #pragma unused(stop)
      [toStr appendString:(isFirst ? msgStartFirst : msgStart)];
      isFirst = NO;

      [toStr appendString:keyLine];
      AppendStringEscaped(key, toStr);
      [toStr appendString:@"\n"];

      [toStr appendString:valueLine];
      switch (valueType) {
        case GPBTypeString:
          AppendStringEscaped(value, toStr);
          break;

        case GPBTypeData:
          AppendBufferAsString(value, toStr);
          break;

        case GPBTypeMessage:
          [toStr appendString:@"{\n"];
          NSString *subIndent = [lineIndent stringByAppendingString:@"    "];
          AppendTextFormatForMessage(value, toStr, subIndent);
          [toStr appendFormat:@"%@  }", lineIndent];
          break;

        default:
          NSCAssert(NO, @"Can't happen");
          break;
      }
      [toStr appendString:@"\n"];

      [toStr appendString:msgEnd];
    }];
  } else {
    // map is one of the GPB*Dictionary classes, type doesn't matter.
    GPBInt32Int32Dictionary *dict = map;
    [dict enumerateForTextFormat:^(id keyObj, id valueObj) {
      [toStr appendString:(isFirst ? msgStartFirst : msgStart)];
      isFirst = NO;

      // Key always is a NSString.
      if (keyType == GPBTypeString) {
        [toStr appendString:keyLine];
        AppendStringEscaped(keyObj, toStr);
        [toStr appendString:@"\n"];
      } else {
        [toStr appendFormat:@"%@%@\n", keyLine, keyObj];
      }

      [toStr appendString:valueLine];
      switch (valueType) {
        case GPBTypeString:
          AppendStringEscaped(valueObj, toStr);
          break;

        case GPBTypeData:
          AppendBufferAsString(valueObj, toStr);
          break;

        case GPBTypeMessage:
          [toStr appendString:@"{\n"];
          NSString *subIndent = [lineIndent stringByAppendingString:@"    "];
          AppendTextFormatForMessage(valueObj, toStr, subIndent);
          [toStr appendFormat:@"%@  }", lineIndent];
          break;

        case GPBTypeEnum: {
          int32_t enumValue = [valueObj intValue];
          NSString *valueStr = nil;
          GPBEnumDescriptor *descriptor = field.enumDescriptor;
          if (descriptor) {
            valueStr = [descriptor textFormatNameForValue:enumValue];
          }
          if (valueStr) {
            [toStr appendString:valueStr];
          } else {
            [toStr appendFormat:@"%d", enumValue];
          }
          break;
        }

        default:
          NSCAssert(valueType != GPBTypeGroup, @"Can't happen");
          // Everything else is a NSString.
          [toStr appendString:valueObj];
          break;
      }
      [toStr appendString:@"\n"];

      [toStr appendString:msgEnd];
    }];
  }
}

static void AppendTextFormatForMessageField(GPBMessage *message,
                                            GPBFieldDescriptor *field,
                                            NSMutableString *toStr,
                                            NSString *lineIndent) {
  id arrayOrMap;
  NSUInteger count;
  GPBFieldType fieldType = field.fieldType;
  switch (fieldType) {
    case GPBFieldTypeSingle:
      arrayOrMap = nil;
      count = (GPBGetHasIvarField(message, field) ? 1 : 0);
      break;

    case GPBFieldTypeRepeated:
      // Will be NSArray or GPB*Array, type doesn't matter, they both
      // implement count.
      arrayOrMap = GPBGetObjectIvarWithFieldNoAutocreate(message, field);
      count = [(NSArray *)arrayOrMap count];
      break;

    case GPBFieldTypeMap: {
      // Will be GPB*Dictionary or NSMutableDictionary, type doesn't matter,
      // they both implement count.
      arrayOrMap = GPBGetObjectIvarWithFieldNoAutocreate(message, field);
      count = [(NSDictionary *)arrayOrMap count];
      break;
    }
  }

  if (count == 0) {
    // Nothing to print, out of here.
    return;
  }

  NSString *lineEnding = @"";

  // If the name can't be reversed or support for extra info was turned off,
  // this can return nil.
  NSString *fieldName = [field textFormatName];
  if ([fieldName length] == 0) {
    fieldName = [NSString stringWithFormat:@"%u", GPBFieldNumber(field)];
    // If there is only one entry, put the objc name as a comment, other wise
    // add it before the the repeated values.
    if (count > 1) {
      [toStr appendFormat:@"%@# %@\n", lineIndent, field.name];
    } else {
      lineEnding = [NSString stringWithFormat:@"  # %@", field.name];
    }
  }

  if (fieldType == GPBFieldTypeMap) {
    AppendTextFormatForMapMessageField(arrayOrMap, field, toStr, lineIndent,
                                       fieldName, lineEnding);
    return;
  }

  id array = arrayOrMap;
  const BOOL isRepeated = (array != nil);

  GPBType fieldDataType = GPBGetFieldType(field);
  BOOL isMessageField = GPBTypeIsMessage(fieldDataType);
  for (NSUInteger j = 0; j < count; ++j) {
    // Start the line.
    [toStr appendFormat:@"%@%@%s ", lineIndent, fieldName,
                        (isMessageField ? "" : ":")];

    // The value.
    switch (fieldDataType) {
#define FIELD_CASE(GPBTYPE, CTYPE, ARRAY_TYPE, ...)                          \
  case GPBType##GPBTYPE: {                                                   \
    CTYPE v = (isRepeated ? [(GPB##ARRAY_TYPE##Array *)array valueAtIndex:j] \
                          : GPBGet##GPBTYPE##IvarWithField(message, field)); \
    [toStr appendFormat:__VA_ARGS__, v];                                     \
    break;                                                                   \
  }

      FIELD_CASE(Int32, int32_t, Int32, @"%d")
      FIELD_CASE(SInt32, int32_t, Int32, @"%d")
      FIELD_CASE(SFixed32, int32_t, Int32, @"%d")
      FIELD_CASE(UInt32, uint32_t, UInt32, @"%u")
      FIELD_CASE(Fixed32, uint32_t, UInt32, @"%u")
      FIELD_CASE(Int64, int64_t, Int64, @"%lld")
      FIELD_CASE(SInt64, int64_t, Int64, @"%lld")
      FIELD_CASE(SFixed64, int64_t, Int64, @"%lld")
      FIELD_CASE(UInt64, uint64_t, UInt64, @"%llu")
      FIELD_CASE(Fixed64, uint64_t, UInt64, @"%llu")
      FIELD_CASE(Float, float, Float, @"%.*g", FLT_DIG)
      FIELD_CASE(Double, double, Double, @"%.*lg", DBL_DIG)

#undef FIELD_CASE

      case GPBTypeEnum: {
        int32_t v = (isRepeated ? [(GPBEnumArray *)array rawValueAtIndex:j]
                                : GPBGetInt32IvarWithField(message, field));
        NSString *valueStr = nil;
        GPBEnumDescriptor *descriptor = field.enumDescriptor;
        if (descriptor) {
          valueStr = [descriptor textFormatNameForValue:v];
        }
        if (valueStr) {
          [toStr appendString:valueStr];
        } else {
          [toStr appendFormat:@"%d", v];
        }
        break;
      }

      case GPBTypeBool: {
        BOOL v = (isRepeated ? [(GPBBoolArray *)array valueAtIndex:j]
                             : GPBGetBoolIvarWithField(message, field));
        [toStr appendString:(v ? @"true" : @"false")];
        break;
      }

      case GPBTypeString: {
        NSString *v = (isRepeated ? [(NSArray *)array objectAtIndex:j]
                                  : GPBGetStringIvarWithField(message, field));
        AppendStringEscaped(v, toStr);
        break;
      }

      case GPBTypeData: {
        NSData *v = (isRepeated ? [(NSArray *)array objectAtIndex:j]
                                : GPBGetDataIvarWithField(message, field));
        AppendBufferAsString(v, toStr);
        break;
      }

      case GPBTypeGroup:
      case GPBTypeMessage: {
        GPBMessage *v =
            (isRepeated ? [(NSArray *)array objectAtIndex:j]
                        : GPBGetObjectIvarWithField(message, field));
        [toStr appendFormat:@"{%@\n", lineEnding];
        NSString *subIndent = [lineIndent stringByAppendingString:@"  "];
        AppendTextFormatForMessage(v, toStr, subIndent);
        [toStr appendFormat:@"%@}", lineIndent];
        lineEnding = @"";
        break;
      }

    }  // switch(fieldDataType)

    // End the line.
    [toStr appendFormat:@"%@\n", lineEnding];

  }  // for(count)
}

static void AppendTextFormatForMessageExtensionRange(GPBMessage *message,
                                                     NSArray *activeExtensions,
                                                     GPBExtensionRange range,
                                                     NSMutableString *toStr,
                                                     NSString *lineIndent) {
  uint32_t start = range.start;
  uint32_t end = range.end;
  for (GPBExtensionField *extension in activeExtensions) {
    uint32_t fieldNumber = extension.fieldNumber;
    if (fieldNumber < start) {
      // Not there yet.
      continue;
    }
    if (fieldNumber > end) {
      // Done.
      break;
    }

    id rawExtValue = [message getExtension:extension];
    GPBExtensionDescriptor *extDescriptor = [extension descriptor];
    BOOL isRepeated = extDescriptor.isRepeated;

    NSUInteger numValues = 1;
    NSString *lineEnding = @"";
    if (isRepeated) {
      numValues = [(NSArray *)rawExtValue count];
    }

    NSString *singletonName = extension.descriptor.singletonName;
    if (numValues == 1) {
      lineEnding = [NSString stringWithFormat:@"  # [%@]", singletonName];
    } else {
      [toStr appendFormat:@"%@# [%@]\n", lineIndent, singletonName];
    }

    GPBType extType = extDescriptor.type;
    for (NSUInteger j = 0; j < numValues; ++j) {
      id curValue = (isRepeated ? [rawExtValue objectAtIndex:j] : rawExtValue);

      // Start the line.
      [toStr appendFormat:@"%@%u%s ", lineIndent, fieldNumber,
                          (GPBTypeIsMessage(extType) ? "" : ":")];

      // The value.
      switch (extType) {
#define FIELD_CASE(GPBTYPE, CTYPE, NUMSELECTOR, ...) \
  case GPBType##GPBTYPE: {                           \
    CTYPE v = [(NSNumber *)curValue NUMSELECTOR];    \
    [toStr appendFormat:__VA_ARGS__, v];             \
    break;                                           \
  }

        FIELD_CASE(Int32, int32_t, intValue, @"%d")
        FIELD_CASE(SInt32, int32_t, intValue, @"%d")
        FIELD_CASE(SFixed32, int32_t, unsignedIntValue, @"%d")
        FIELD_CASE(UInt32, uint32_t, unsignedIntValue, @"%u")
        FIELD_CASE(Fixed32, uint32_t, unsignedIntValue, @"%u")
        FIELD_CASE(Int64, int64_t, longLongValue, @"%lld")
        FIELD_CASE(SInt64, int64_t, longLongValue, @"%lld")
        FIELD_CASE(SFixed64, int64_t, longLongValue, @"%lld")
        FIELD_CASE(UInt64, uint64_t, unsignedLongLongValue, @"%llu")
        FIELD_CASE(Fixed64, uint64_t, unsignedLongLongValue, @"%llu")
        FIELD_CASE(Float, float, floatValue, @"%.*g", FLT_DIG)
        FIELD_CASE(Double, double, doubleValue, @"%.*lg", DBL_DIG)
        // TODO: Add a comment with the enum name from enum descriptors
        // (might not be real value, so leave it as a comment, ObjC compiler
        // name mangles differently).  Doesn't look like we actually generate
        // an enum descriptor reference like we do for normal fields, so this
        // will take a compiler change.
        FIELD_CASE(Enum, int32_t, intValue, @"%d")

#undef FIELD_CASE

        case GPBTypeBool:
          [toStr appendString:([(NSNumber *)curValue boolValue] ? @"true"
                                                                : @"false")];
          break;

        case GPBTypeString:
          AppendStringEscaped(curValue, toStr);
          break;

        case GPBTypeData:
          AppendBufferAsString((NSData *)curValue, toStr);
          break;

        case GPBTypeGroup:
        case GPBTypeMessage: {
          [toStr appendFormat:@"{%@\n", lineEnding];
          NSString *subIndent = [lineIndent stringByAppendingString:@"  "];
          AppendTextFormatForMessage(curValue, toStr, subIndent);
          [toStr appendFormat:@"%@}", lineIndent];
          lineEnding = @"";
          break;
        }

      }  // switch(extType)

    }  //  for(numValues)

    // End the line.
    [toStr appendFormat:@"%@\n", lineEnding];

  }  // for..in(activeExtensions)
}

static void AppendTextFormatForMessage(GPBMessage *message,
                                       NSMutableString *toStr,
                                       NSString *lineIndent) {
  GPBDescriptor *descriptor = [message descriptor];
  NSArray *fieldsArray = descriptor->fields_;
  NSUInteger fieldCount = fieldsArray.count;
  const GPBExtensionRange *extensionRanges = descriptor.extensionRanges;
  NSUInteger extensionRangesCount = descriptor.extensionRangesCount;
  NSArray *activeExtensions = [message sortedExtensionsInUse];
  for (NSUInteger i = 0, j = 0; i < fieldCount || j < extensionRangesCount;) {
    if (i == fieldCount) {
      AppendTextFormatForMessageExtensionRange(
          message, activeExtensions, extensionRanges[j++], toStr, lineIndent);
    } else if (j == extensionRangesCount ||
               GPBFieldNumber(fieldsArray[i]) < extensionRanges[j].start) {
      AppendTextFormatForMessageField(message, fieldsArray[i++], toStr,
                                      lineIndent);
    } else {
      AppendTextFormatForMessageExtensionRange(
          message, activeExtensions, extensionRanges[j++], toStr, lineIndent);
    }
  }

  NSString *unknownFieldsStr =
      GPBTextFormatForUnknownFieldSet(message.unknownFields, lineIndent);
  if ([unknownFieldsStr length] > 0) {
    [toStr appendFormat:@"%@# --- Unknown fields ---\n", lineIndent];
    [toStr appendString:unknownFieldsStr];
  }
}

NSString *GPBTextFormatForMessage(GPBMessage *message, NSString *lineIndent) {
  if (message == nil) return nil;
  if (lineIndent == nil) lineIndent = @"";

  NSMutableString *buildString = [NSMutableString string];
  AppendTextFormatForMessage(message, buildString, lineIndent);
  return buildString;
}

NSString *GPBTextFormatForUnknownFieldSet(GPBUnknownFieldSet *unknownSet,
                                          NSString *lineIndent) {
  if (unknownSet == nil) return nil;
  if (lineIndent == nil) lineIndent = @"";

  NSMutableString *result = [NSMutableString string];
  for (GPBField *field in [unknownSet sortedFields]) {
    int32_t fieldNumber = [field number];

#define PRINT_LOOP(PROPNAME, CTYPE, FORMAT)                                   \
  [field.PROPNAME                                                             \
      enumerateValuesWithBlock:^(CTYPE value, NSUInteger idx, BOOL * stop) {  \
    _Pragma("unused(idx, stop)");                                             \
    [result                                                                   \
        appendFormat:@"%@%d: " #FORMAT "\n", lineIndent, fieldNumber, value]; \
      }];

    PRINT_LOOP(varintList, uint64_t, %llu);
    PRINT_LOOP(fixed32List, uint32_t, 0x%X);
    PRINT_LOOP(fixed64List, uint64_t, 0x%llX);

#undef PRINT_LOOP

    // NOTE: C++ version of TextFormat tries to parse this as a message
    // and print that if it succeeds.
    for (NSData *data in field.lengthDelimitedList) {
      [result appendFormat:@"%@%d: ", lineIndent, fieldNumber];
      AppendBufferAsString(data, result);
      [result appendString:@"\n"];
    }

    for (GPBUnknownFieldSet *subUnknownSet in field.groupList) {
      [result appendFormat:@"%@%d: {\n", lineIndent, fieldNumber];
      NSString *subIndent = [lineIndent stringByAppendingString:@"  "];
      NSString *subUnknwonSetStr =
          GPBTextFormatForUnknownFieldSet(subUnknownSet, subIndent);
      [result appendString:subUnknwonSetStr];
      [result appendFormat:@"%@}\n", lineIndent];
    }
  }
  return result;
}

// Helpers to decode a varint. Not using GPBCodedInputStream version because
// that needs a state object, and we don't want to create an input stream out
// of the data.
static inline int8_t ReadRawByteFromData(const uint8_t **data) {
  int8_t result = *((int8_t *)(*data));
  ++(*data);
  return result;
}

static inline int32_t ReadRawVarint32FromData(const uint8_t **data) {
  int8_t tmp = ReadRawByteFromData(data);
  if (tmp >= 0) {
    return tmp;
  }
  int32_t result = tmp & 0x7f;
  if ((tmp = ReadRawByteFromData(data)) >= 0) {
    result |= tmp << 7;
  } else {
    result |= (tmp & 0x7f) << 7;
    if ((tmp = ReadRawByteFromData(data)) >= 0) {
      result |= tmp << 14;
    } else {
      result |= (tmp & 0x7f) << 14;
      if ((tmp = ReadRawByteFromData(data)) >= 0) {
        result |= tmp << 21;
      } else {
        result |= (tmp & 0x7f) << 21;
        result |= (tmp = ReadRawByteFromData(data)) << 28;
        if (tmp < 0) {
          // Discard upper 32 bits.
          for (int i = 0; i < 5; i++) {
            if (ReadRawByteFromData(data) >= 0) {
              return result;
            }
          }
          [NSException raise:NSParseErrorException
                      format:@"Unable to read varint32"];
        }
      }
    }
  }
  return result;
}

NSString *GPBDecodeTextFormatName(const uint8_t *decodeData, int32_t key,
                                  NSString *inputStr) {
  // decodData form:
  //  varint32: num entries
  //  for each entry:
  //    varint32: key
  //    bytes*: decode data
  //
  // decode data one of two forms:
  //  1: a \0 followed by the string followed by an \0
  //  2: bytecodes to transform an input into the right thing, ending with \0
  //
  // the bytes codes are of the form:
  //  0xabbccccc
  //  0x0 (all zeros), end.
  //  a - if set, add an underscore
  //  bb - 00 ccccc bytes as is
  //  bb - 10 ccccc upper first, as is on rest, ccccc byte total
  //  bb - 01 ccccc lower first, as is on rest, ccccc byte total
  //  bb - 11 ccccc all upper, ccccc byte total

  if (!decodeData || !inputStr) {
    return nil;
  }

  // Find key
  const uint8_t *scan = decodeData;
  int32_t numEntries = ReadRawVarint32FromData(&scan);
  BOOL foundKey = NO;
  while (!foundKey && (numEntries > 0)) {
    --numEntries;
    int32_t dataKey = ReadRawVarint32FromData(&scan);
    if (dataKey == key) {
      foundKey = YES;
    } else {
      // If it is a inlined string, it will start with \0; if it is bytecode it
      // will start with a code. So advance one (skipping the inline string
      // marker), and then loop until reaching the end marker (\0).
      ++scan;
      while (*scan != 0) ++scan;
      // Now move past the end marker.
      ++scan;
    }
  }

  if (!foundKey) {
    return nil;
  }

  // Decode

  if (*scan == 0) {
    // Inline string. Move over the marker, and NSString can take it as
    // UTF8.
    ++scan;
    NSString *result = [NSString stringWithUTF8String:(const char *)scan];
    return result;
  }

  NSMutableString *result =
      [NSMutableString stringWithCapacity:[inputStr length]];

  const uint8_t kAddUnderscore  = 0b10000000;
  const uint8_t kOpMask         = 0b01100000;
  // const uint8_t kOpAsIs        = 0b00000000;
  const uint8_t kOpFirstUpper     = 0b01000000;
  const uint8_t kOpFirstLower     = 0b00100000;
  const uint8_t kOpAllUpper       = 0b01100000;
  const uint8_t kSegmentLenMask = 0b00011111;

  NSInteger i = 0;
  for (; *scan != 0; ++scan) {
    if (*scan & kAddUnderscore) {
      [result appendString:@"_"];
    }
    int segmentLen = *scan & kSegmentLenMask;
    uint8_t decodeOp = *scan & kOpMask;

    // Do op specific handling of the first character.
    if (decodeOp == kOpFirstUpper) {
      unichar c = [inputStr characterAtIndex:i];
      [result appendFormat:@"%c", toupper((char)c)];
      ++i;
      --segmentLen;
    } else if (decodeOp == kOpFirstLower) {
      unichar c = [inputStr characterAtIndex:i];
      [result appendFormat:@"%c", tolower((char)c)];
      ++i;
      --segmentLen;
    }
    // else op == kOpAsIs || op == kOpAllUpper

    // Now pull over the rest of the length for this segment.
    for (int x = 0; x < segmentLen; ++x) {
      unichar c = [inputStr characterAtIndex:(i + x)];
      if (decodeOp == kOpAllUpper) {
        [result appendFormat:@"%c", toupper((char)c)];
      } else {
        [result appendFormat:@"%C", c];
      }
    }
    i += segmentLen;
  }

  return result;
}

#pragma mark - GPBMessageSignatureProtocol

// A series of selectors that are used solely to get @encoding values
// for them by the dynamic protobuf runtime code. An object using the protocol
// needs to be declared for the protocol to be valid at runtime.
@interface GPBMessageSignatureProtocol : NSObject<GPBMessageSignatureProtocol>
@end
@implementation GPBMessageSignatureProtocol
@end
