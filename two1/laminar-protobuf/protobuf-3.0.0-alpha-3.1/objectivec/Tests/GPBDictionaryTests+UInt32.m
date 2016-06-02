// Protocol Buffers - Google's data interchange format
// Copyright 2015 Google Inc.  All rights reserved.
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

#import <Foundation/Foundation.h>
#import <XCTest/XCTest.h>

#import "GPBDictionary.h"

#import "GPBTestUtilities.h"
#import "google/protobuf/UnittestRuntimeProto2.pbobjc.h"

// Pull in the macros (using an external file because expanding all tests
// in a single file makes a file that is failing to work with within Xcode.
//%PDDM-IMPORT-DEFINES GPBDictionaryTests.pddm

//%PDDM-EXPAND TEST_FOR_POD_KEY(UInt32, uint32_t, 1U, 2U, 3U, 4U)
// This block of code is generated, do not edit it directly.

// To let the testing macros work, add some extra methods to simplify things.
@interface GPBUInt32EnumDictionary (TestingTweak)
+ (instancetype)dictionaryWithValue:(int32_t)value forKey:(uint32_t)key;
- (instancetype)initWithValues:(const int32_t [])values
                       forKeys:(const uint32_t [])keys
                         count:(NSUInteger)count;
@end

static BOOL TestingEnum_IsValidValue(int32_t value) {
  switch (value) {
    case 700:
    case 701:
    case 702:
    case 703:
      return YES;
    default:
      return NO;
  }
}

@implementation GPBUInt32EnumDictionary (TestingTweak)
+ (instancetype)dictionaryWithValue:(int32_t)value forKey:(uint32_t)key {
  // Cast is needed to compiler knows what class we are invoking initWithValues: on to get the
  // type correct.
  return [[(GPBUInt32EnumDictionary*)[self alloc] initWithValidationFunction:TestingEnum_IsValidValue
                                                                   rawValues:&value
                                                                     forKeys:&key
                                                                       count:1] autorelease];
}
- (instancetype)initWithValues:(const int32_t [])values
                       forKeys:(const uint32_t [])keys
                         count:(NSUInteger)count {
  return [self initWithValidationFunction:TestingEnum_IsValidValue
                                rawValues:values
                                  forKeys:keys
                                    count:count];
}
@end


#pragma mark - UInt32 -> UInt32

@interface GPBUInt32UInt32DictionaryTests : XCTestCase
@end

@implementation GPBUInt32UInt32DictionaryTests

- (void)testEmpty {
  GPBUInt32UInt32Dictionary *dict = [[GPBUInt32UInt32Dictionary alloc] init];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, uint32_t aValue, BOOL *stop) {
    #pragma unused(aKey, aValue, stop)
    XCTFail(@"Shouldn't get here!");
  }];
  [dict release];
}

- (void)testOne {
  GPBUInt32UInt32Dictionary *dict = [GPBUInt32UInt32Dictionary dictionaryWithValue:100U forKey:1U];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 1U);
  uint32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 100U);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, uint32_t aValue, BOOL *stop) {
    XCTAssertEqual(aKey, 1U);
    XCTAssertEqual(aValue, 100U);
    XCTAssertNotEqual(stop, NULL);
  }];
}

- (void)testBasics {
  const uint32_t kKeys[] = { 1U, 2U, 3U };
  const uint32_t kValues[] = { 100U, 101U, 102U };
  GPBUInt32UInt32Dictionary *dict =
      [[GPBUInt32UInt32Dictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 3U);
  uint32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 100U);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 101U);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 102U);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  __block NSUInteger idx = 0;
  uint32_t *seenKeys = malloc(3 * sizeof(uint32_t));
  uint32_t *seenValues = malloc(3 * sizeof(uint32_t));
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, uint32_t aValue, BOOL *stop) {
    XCTAssertLessThan(idx, 3U);
    seenKeys[idx] = aKey;
    seenValues[idx] = aValue;
    XCTAssertNotEqual(stop, NULL);
    ++idx;
  }];
  for (int i = 0; i < 3; ++i) {
    BOOL foundKey = NO;
    for (int j = 0; (j < 3) && !foundKey; ++j) {
      if (kKeys[i] == seenKeys[j]) {
        foundKey = YES;
        XCTAssertEqual(kValues[i], seenValues[j], @"i = %d, j = %d", i, j);
      }
    }
    XCTAssertTrue(foundKey, @"i = %d", i);
  }
  free(seenKeys);
  free(seenValues);

  // Stopping the enumeration.
  idx = 0;
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, uint32_t aValue, BOOL *stop) {
    #pragma unused(aKey, aValue)
    if (idx == 1) *stop = YES;
    XCTAssertNotEqual(idx, 2U);
    ++idx;
  }];
  [dict release];
}

- (void)testEquality {
  const uint32_t kKeys1[] = { 1U, 2U, 3U, 4U };
  const uint32_t kKeys2[] = { 2U, 1U, 4U };
  const uint32_t kValues1[] = { 100U, 101U, 102U };
  const uint32_t kValues2[] = { 100U, 103U, 102U };
  const uint32_t kValues3[] = { 100U, 101U, 102U, 103U };
  GPBUInt32UInt32Dictionary *dict1 =
      [[GPBUInt32UInt32Dictionary alloc] initWithValues:kValues1
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1);
  GPBUInt32UInt32Dictionary *dict1prime =
      [[GPBUInt32UInt32Dictionary alloc] initWithValues:kValues1
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1prime);
  GPBUInt32UInt32Dictionary *dict2 =
      [[GPBUInt32UInt32Dictionary alloc] initWithValues:kValues2
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  GPBUInt32UInt32Dictionary *dict3 =
      [[GPBUInt32UInt32Dictionary alloc] initWithValues:kValues1
                                                forKeys:kKeys2
                                                  count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict3);
  GPBUInt32UInt32Dictionary *dict4 =
      [[GPBUInt32UInt32Dictionary alloc] initWithValues:kValues3
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues3)];
  XCTAssertNotNil(dict4);

  // 1/1Prime should be different objects, but equal.
  XCTAssertNotEqual(dict1, dict1prime);
  XCTAssertEqualObjects(dict1, dict1prime);
  // Equal, so they must have same hash.
  XCTAssertEqual([dict1 hash], [dict1prime hash]);

  // 2 is save keys, different values; not equal.
  XCTAssertNotEqualObjects(dict1, dict2);

  // 3 is different keys, samae values; not equal.
  XCTAssertNotEqualObjects(dict1, dict3);

  // 4 extra pair; not equal
  XCTAssertNotEqualObjects(dict1, dict4);

  [dict1 release];
  [dict1prime release];
  [dict2 release];
  [dict3 release];
  [dict4 release];
}

- (void)testCopy {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const uint32_t kValues[] = { 100U, 101U, 102U, 103U };
  GPBUInt32UInt32Dictionary *dict =
      [[GPBUInt32UInt32Dictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32UInt32Dictionary *dict2 = [dict copy];
  XCTAssertNotNil(dict2);

  // Should be new object but equal.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  XCTAssertTrue([dict2 isKindOfClass:[GPBUInt32UInt32Dictionary class]]);

  [dict2 release];
  [dict release];
}

- (void)testDictionaryFromDictionary {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const uint32_t kValues[] = { 100U, 101U, 102U, 103U };
  GPBUInt32UInt32Dictionary *dict =
      [[GPBUInt32UInt32Dictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32UInt32Dictionary *dict2 =
      [GPBUInt32UInt32Dictionary dictionaryWithDictionary:dict];
  XCTAssertNotNil(dict2);

  // Should be new pointer, but equal objects.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  [dict release];
}

- (void)testAdds {
  GPBUInt32UInt32Dictionary *dict = [GPBUInt32UInt32Dictionary dictionary];
  XCTAssertNotNil(dict);

  XCTAssertEqual(dict.count, 0U);
  [dict setValue:100U forKey:1U];
  XCTAssertEqual(dict.count, 1U);

  const uint32_t kKeys[] = { 2U, 3U, 4U };
  const uint32_t kValues[] = { 101U, 102U, 103U };
  GPBUInt32UInt32Dictionary *dict2 =
      [[GPBUInt32UInt32Dictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);

  uint32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 100U);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 101U);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 102U);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 103U);
  [dict2 release];
}

- (void)testRemove {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const uint32_t kValues[] = { 100U, 101U, 102U, 103U };
  GPBUInt32UInt32Dictionary *dict =
      [[GPBUInt32UInt32Dictionary alloc] initWithValues:kValues
                                         forKeys:kKeys
                                           count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);

  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  uint32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 100U);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 102U);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 103U);

  // Remove again does nothing.
  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 100U);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 102U);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 103U);

  [dict removeValueForKey:4U];
  XCTAssertEqual(dict.count, 2U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 100U);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 102U);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  [dict removeAll];
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertFalse([dict valueForKey:3U value:NULL]);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);
  [dict release];
}

- (void)testInplaceMutation {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const uint32_t kValues[] = { 100U, 101U, 102U, 103U };
  GPBUInt32UInt32Dictionary *dict =
      [[GPBUInt32UInt32Dictionary alloc] initWithValues:kValues
                                         forKeys:kKeys
                                           count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);
  uint32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 100U);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 101U);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 102U);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 103U);

  [dict setValue:103U forKey:1U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 103U);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 101U);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 102U);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 103U);

  [dict setValue:101U forKey:4U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 103U);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 101U);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 102U);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 101U);

  const uint32_t kKeys2[] = { 2U, 3U };
  const uint32_t kValues2[] = { 102U, 100U };
  GPBUInt32UInt32Dictionary *dict2 =
      [[GPBUInt32UInt32Dictionary alloc] initWithValues:kValues2
                                                forKeys:kKeys2
                                                  count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 103U);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 102U);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 100U);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 101U);

  [dict2 release];
  [dict release];
}

@end

#pragma mark - UInt32 -> Int32

@interface GPBUInt32Int32DictionaryTests : XCTestCase
@end

@implementation GPBUInt32Int32DictionaryTests

- (void)testEmpty {
  GPBUInt32Int32Dictionary *dict = [[GPBUInt32Int32Dictionary alloc] init];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, int32_t aValue, BOOL *stop) {
    #pragma unused(aKey, aValue, stop)
    XCTFail(@"Shouldn't get here!");
  }];
  [dict release];
}

- (void)testOne {
  GPBUInt32Int32Dictionary *dict = [GPBUInt32Int32Dictionary dictionaryWithValue:200 forKey:1U];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 1U);
  int32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 200);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, int32_t aValue, BOOL *stop) {
    XCTAssertEqual(aKey, 1U);
    XCTAssertEqual(aValue, 200);
    XCTAssertNotEqual(stop, NULL);
  }];
}

- (void)testBasics {
  const uint32_t kKeys[] = { 1U, 2U, 3U };
  const int32_t kValues[] = { 200, 201, 202 };
  GPBUInt32Int32Dictionary *dict =
      [[GPBUInt32Int32Dictionary alloc] initWithValues:kValues
                                               forKeys:kKeys
                                                 count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 3U);
  int32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 200);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 201);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 202);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  __block NSUInteger idx = 0;
  uint32_t *seenKeys = malloc(3 * sizeof(uint32_t));
  int32_t *seenValues = malloc(3 * sizeof(int32_t));
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, int32_t aValue, BOOL *stop) {
    XCTAssertLessThan(idx, 3U);
    seenKeys[idx] = aKey;
    seenValues[idx] = aValue;
    XCTAssertNotEqual(stop, NULL);
    ++idx;
  }];
  for (int i = 0; i < 3; ++i) {
    BOOL foundKey = NO;
    for (int j = 0; (j < 3) && !foundKey; ++j) {
      if (kKeys[i] == seenKeys[j]) {
        foundKey = YES;
        XCTAssertEqual(kValues[i], seenValues[j], @"i = %d, j = %d", i, j);
      }
    }
    XCTAssertTrue(foundKey, @"i = %d", i);
  }
  free(seenKeys);
  free(seenValues);

  // Stopping the enumeration.
  idx = 0;
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, int32_t aValue, BOOL *stop) {
    #pragma unused(aKey, aValue)
    if (idx == 1) *stop = YES;
    XCTAssertNotEqual(idx, 2U);
    ++idx;
  }];
  [dict release];
}

- (void)testEquality {
  const uint32_t kKeys1[] = { 1U, 2U, 3U, 4U };
  const uint32_t kKeys2[] = { 2U, 1U, 4U };
  const int32_t kValues1[] = { 200, 201, 202 };
  const int32_t kValues2[] = { 200, 203, 202 };
  const int32_t kValues3[] = { 200, 201, 202, 203 };
  GPBUInt32Int32Dictionary *dict1 =
      [[GPBUInt32Int32Dictionary alloc] initWithValues:kValues1
                                               forKeys:kKeys1
                                                 count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1);
  GPBUInt32Int32Dictionary *dict1prime =
      [[GPBUInt32Int32Dictionary alloc] initWithValues:kValues1
                                               forKeys:kKeys1
                                                 count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1prime);
  GPBUInt32Int32Dictionary *dict2 =
      [[GPBUInt32Int32Dictionary alloc] initWithValues:kValues2
                                               forKeys:kKeys1
                                                 count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  GPBUInt32Int32Dictionary *dict3 =
      [[GPBUInt32Int32Dictionary alloc] initWithValues:kValues1
                                               forKeys:kKeys2
                                                 count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict3);
  GPBUInt32Int32Dictionary *dict4 =
      [[GPBUInt32Int32Dictionary alloc] initWithValues:kValues3
                                               forKeys:kKeys1
                                                 count:GPBARRAYSIZE(kValues3)];
  XCTAssertNotNil(dict4);

  // 1/1Prime should be different objects, but equal.
  XCTAssertNotEqual(dict1, dict1prime);
  XCTAssertEqualObjects(dict1, dict1prime);
  // Equal, so they must have same hash.
  XCTAssertEqual([dict1 hash], [dict1prime hash]);

  // 2 is save keys, different values; not equal.
  XCTAssertNotEqualObjects(dict1, dict2);

  // 3 is different keys, samae values; not equal.
  XCTAssertNotEqualObjects(dict1, dict3);

  // 4 extra pair; not equal
  XCTAssertNotEqualObjects(dict1, dict4);

  [dict1 release];
  [dict1prime release];
  [dict2 release];
  [dict3 release];
  [dict4 release];
}

- (void)testCopy {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int32_t kValues[] = { 200, 201, 202, 203 };
  GPBUInt32Int32Dictionary *dict =
      [[GPBUInt32Int32Dictionary alloc] initWithValues:kValues
                                               forKeys:kKeys
                                                 count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32Int32Dictionary *dict2 = [dict copy];
  XCTAssertNotNil(dict2);

  // Should be new object but equal.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  XCTAssertTrue([dict2 isKindOfClass:[GPBUInt32Int32Dictionary class]]);

  [dict2 release];
  [dict release];
}

- (void)testDictionaryFromDictionary {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int32_t kValues[] = { 200, 201, 202, 203 };
  GPBUInt32Int32Dictionary *dict =
      [[GPBUInt32Int32Dictionary alloc] initWithValues:kValues
                                               forKeys:kKeys
                                                 count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32Int32Dictionary *dict2 =
      [GPBUInt32Int32Dictionary dictionaryWithDictionary:dict];
  XCTAssertNotNil(dict2);

  // Should be new pointer, but equal objects.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  [dict release];
}

- (void)testAdds {
  GPBUInt32Int32Dictionary *dict = [GPBUInt32Int32Dictionary dictionary];
  XCTAssertNotNil(dict);

  XCTAssertEqual(dict.count, 0U);
  [dict setValue:200 forKey:1U];
  XCTAssertEqual(dict.count, 1U);

  const uint32_t kKeys[] = { 2U, 3U, 4U };
  const int32_t kValues[] = { 201, 202, 203 };
  GPBUInt32Int32Dictionary *dict2 =
      [[GPBUInt32Int32Dictionary alloc] initWithValues:kValues
                                               forKeys:kKeys
                                                 count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);

  int32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 200);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 201);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 202);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 203);
  [dict2 release];
}

- (void)testRemove {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int32_t kValues[] = { 200, 201, 202, 203 };
  GPBUInt32Int32Dictionary *dict =
      [[GPBUInt32Int32Dictionary alloc] initWithValues:kValues
                                        forKeys:kKeys
                                          count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);

  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  int32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 200);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 202);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 203);

  // Remove again does nothing.
  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 200);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 202);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 203);

  [dict removeValueForKey:4U];
  XCTAssertEqual(dict.count, 2U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 200);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 202);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  [dict removeAll];
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertFalse([dict valueForKey:3U value:NULL]);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);
  [dict release];
}

- (void)testInplaceMutation {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int32_t kValues[] = { 200, 201, 202, 203 };
  GPBUInt32Int32Dictionary *dict =
      [[GPBUInt32Int32Dictionary alloc] initWithValues:kValues
                                        forKeys:kKeys
                                          count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);
  int32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 200);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 201);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 202);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 203);

  [dict setValue:203 forKey:1U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 203);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 201);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 202);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 203);

  [dict setValue:201 forKey:4U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 203);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 201);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 202);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 201);

  const uint32_t kKeys2[] = { 2U, 3U };
  const int32_t kValues2[] = { 202, 200 };
  GPBUInt32Int32Dictionary *dict2 =
      [[GPBUInt32Int32Dictionary alloc] initWithValues:kValues2
                                               forKeys:kKeys2
                                                 count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 203);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 202);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 200);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 201);

  [dict2 release];
  [dict release];
}

@end

#pragma mark - UInt32 -> UInt64

@interface GPBUInt32UInt64DictionaryTests : XCTestCase
@end

@implementation GPBUInt32UInt64DictionaryTests

- (void)testEmpty {
  GPBUInt32UInt64Dictionary *dict = [[GPBUInt32UInt64Dictionary alloc] init];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, uint64_t aValue, BOOL *stop) {
    #pragma unused(aKey, aValue, stop)
    XCTFail(@"Shouldn't get here!");
  }];
  [dict release];
}

- (void)testOne {
  GPBUInt32UInt64Dictionary *dict = [GPBUInt32UInt64Dictionary dictionaryWithValue:300U forKey:1U];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 1U);
  uint64_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 300U);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, uint64_t aValue, BOOL *stop) {
    XCTAssertEqual(aKey, 1U);
    XCTAssertEqual(aValue, 300U);
    XCTAssertNotEqual(stop, NULL);
  }];
}

- (void)testBasics {
  const uint32_t kKeys[] = { 1U, 2U, 3U };
  const uint64_t kValues[] = { 300U, 301U, 302U };
  GPBUInt32UInt64Dictionary *dict =
      [[GPBUInt32UInt64Dictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 3U);
  uint64_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 300U);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 301U);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 302U);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  __block NSUInteger idx = 0;
  uint32_t *seenKeys = malloc(3 * sizeof(uint32_t));
  uint64_t *seenValues = malloc(3 * sizeof(uint64_t));
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, uint64_t aValue, BOOL *stop) {
    XCTAssertLessThan(idx, 3U);
    seenKeys[idx] = aKey;
    seenValues[idx] = aValue;
    XCTAssertNotEqual(stop, NULL);
    ++idx;
  }];
  for (int i = 0; i < 3; ++i) {
    BOOL foundKey = NO;
    for (int j = 0; (j < 3) && !foundKey; ++j) {
      if (kKeys[i] == seenKeys[j]) {
        foundKey = YES;
        XCTAssertEqual(kValues[i], seenValues[j], @"i = %d, j = %d", i, j);
      }
    }
    XCTAssertTrue(foundKey, @"i = %d", i);
  }
  free(seenKeys);
  free(seenValues);

  // Stopping the enumeration.
  idx = 0;
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, uint64_t aValue, BOOL *stop) {
    #pragma unused(aKey, aValue)
    if (idx == 1) *stop = YES;
    XCTAssertNotEqual(idx, 2U);
    ++idx;
  }];
  [dict release];
}

- (void)testEquality {
  const uint32_t kKeys1[] = { 1U, 2U, 3U, 4U };
  const uint32_t kKeys2[] = { 2U, 1U, 4U };
  const uint64_t kValues1[] = { 300U, 301U, 302U };
  const uint64_t kValues2[] = { 300U, 303U, 302U };
  const uint64_t kValues3[] = { 300U, 301U, 302U, 303U };
  GPBUInt32UInt64Dictionary *dict1 =
      [[GPBUInt32UInt64Dictionary alloc] initWithValues:kValues1
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1);
  GPBUInt32UInt64Dictionary *dict1prime =
      [[GPBUInt32UInt64Dictionary alloc] initWithValues:kValues1
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1prime);
  GPBUInt32UInt64Dictionary *dict2 =
      [[GPBUInt32UInt64Dictionary alloc] initWithValues:kValues2
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  GPBUInt32UInt64Dictionary *dict3 =
      [[GPBUInt32UInt64Dictionary alloc] initWithValues:kValues1
                                                forKeys:kKeys2
                                                  count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict3);
  GPBUInt32UInt64Dictionary *dict4 =
      [[GPBUInt32UInt64Dictionary alloc] initWithValues:kValues3
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues3)];
  XCTAssertNotNil(dict4);

  // 1/1Prime should be different objects, but equal.
  XCTAssertNotEqual(dict1, dict1prime);
  XCTAssertEqualObjects(dict1, dict1prime);
  // Equal, so they must have same hash.
  XCTAssertEqual([dict1 hash], [dict1prime hash]);

  // 2 is save keys, different values; not equal.
  XCTAssertNotEqualObjects(dict1, dict2);

  // 3 is different keys, samae values; not equal.
  XCTAssertNotEqualObjects(dict1, dict3);

  // 4 extra pair; not equal
  XCTAssertNotEqualObjects(dict1, dict4);

  [dict1 release];
  [dict1prime release];
  [dict2 release];
  [dict3 release];
  [dict4 release];
}

- (void)testCopy {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const uint64_t kValues[] = { 300U, 301U, 302U, 303U };
  GPBUInt32UInt64Dictionary *dict =
      [[GPBUInt32UInt64Dictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32UInt64Dictionary *dict2 = [dict copy];
  XCTAssertNotNil(dict2);

  // Should be new object but equal.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  XCTAssertTrue([dict2 isKindOfClass:[GPBUInt32UInt64Dictionary class]]);

  [dict2 release];
  [dict release];
}

- (void)testDictionaryFromDictionary {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const uint64_t kValues[] = { 300U, 301U, 302U, 303U };
  GPBUInt32UInt64Dictionary *dict =
      [[GPBUInt32UInt64Dictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32UInt64Dictionary *dict2 =
      [GPBUInt32UInt64Dictionary dictionaryWithDictionary:dict];
  XCTAssertNotNil(dict2);

  // Should be new pointer, but equal objects.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  [dict release];
}

- (void)testAdds {
  GPBUInt32UInt64Dictionary *dict = [GPBUInt32UInt64Dictionary dictionary];
  XCTAssertNotNil(dict);

  XCTAssertEqual(dict.count, 0U);
  [dict setValue:300U forKey:1U];
  XCTAssertEqual(dict.count, 1U);

  const uint32_t kKeys[] = { 2U, 3U, 4U };
  const uint64_t kValues[] = { 301U, 302U, 303U };
  GPBUInt32UInt64Dictionary *dict2 =
      [[GPBUInt32UInt64Dictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);

  uint64_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 300U);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 301U);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 302U);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 303U);
  [dict2 release];
}

- (void)testRemove {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const uint64_t kValues[] = { 300U, 301U, 302U, 303U };
  GPBUInt32UInt64Dictionary *dict =
      [[GPBUInt32UInt64Dictionary alloc] initWithValues:kValues
                                         forKeys:kKeys
                                           count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);

  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  uint64_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 300U);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 302U);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 303U);

  // Remove again does nothing.
  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 300U);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 302U);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 303U);

  [dict removeValueForKey:4U];
  XCTAssertEqual(dict.count, 2U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 300U);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 302U);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  [dict removeAll];
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertFalse([dict valueForKey:3U value:NULL]);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);
  [dict release];
}

- (void)testInplaceMutation {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const uint64_t kValues[] = { 300U, 301U, 302U, 303U };
  GPBUInt32UInt64Dictionary *dict =
      [[GPBUInt32UInt64Dictionary alloc] initWithValues:kValues
                                         forKeys:kKeys
                                           count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);
  uint64_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 300U);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 301U);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 302U);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 303U);

  [dict setValue:303U forKey:1U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 303U);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 301U);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 302U);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 303U);

  [dict setValue:301U forKey:4U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 303U);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 301U);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 302U);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 301U);

  const uint32_t kKeys2[] = { 2U, 3U };
  const uint64_t kValues2[] = { 302U, 300U };
  GPBUInt32UInt64Dictionary *dict2 =
      [[GPBUInt32UInt64Dictionary alloc] initWithValues:kValues2
                                                forKeys:kKeys2
                                                  count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 303U);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 302U);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 300U);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 301U);

  [dict2 release];
  [dict release];
}

@end

#pragma mark - UInt32 -> Int64

@interface GPBUInt32Int64DictionaryTests : XCTestCase
@end

@implementation GPBUInt32Int64DictionaryTests

- (void)testEmpty {
  GPBUInt32Int64Dictionary *dict = [[GPBUInt32Int64Dictionary alloc] init];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, int64_t aValue, BOOL *stop) {
    #pragma unused(aKey, aValue, stop)
    XCTFail(@"Shouldn't get here!");
  }];
  [dict release];
}

- (void)testOne {
  GPBUInt32Int64Dictionary *dict = [GPBUInt32Int64Dictionary dictionaryWithValue:400 forKey:1U];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 1U);
  int64_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 400);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, int64_t aValue, BOOL *stop) {
    XCTAssertEqual(aKey, 1U);
    XCTAssertEqual(aValue, 400);
    XCTAssertNotEqual(stop, NULL);
  }];
}

- (void)testBasics {
  const uint32_t kKeys[] = { 1U, 2U, 3U };
  const int64_t kValues[] = { 400, 401, 402 };
  GPBUInt32Int64Dictionary *dict =
      [[GPBUInt32Int64Dictionary alloc] initWithValues:kValues
                                               forKeys:kKeys
                                                 count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 3U);
  int64_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 400);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 401);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 402);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  __block NSUInteger idx = 0;
  uint32_t *seenKeys = malloc(3 * sizeof(uint32_t));
  int64_t *seenValues = malloc(3 * sizeof(int64_t));
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, int64_t aValue, BOOL *stop) {
    XCTAssertLessThan(idx, 3U);
    seenKeys[idx] = aKey;
    seenValues[idx] = aValue;
    XCTAssertNotEqual(stop, NULL);
    ++idx;
  }];
  for (int i = 0; i < 3; ++i) {
    BOOL foundKey = NO;
    for (int j = 0; (j < 3) && !foundKey; ++j) {
      if (kKeys[i] == seenKeys[j]) {
        foundKey = YES;
        XCTAssertEqual(kValues[i], seenValues[j], @"i = %d, j = %d", i, j);
      }
    }
    XCTAssertTrue(foundKey, @"i = %d", i);
  }
  free(seenKeys);
  free(seenValues);

  // Stopping the enumeration.
  idx = 0;
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, int64_t aValue, BOOL *stop) {
    #pragma unused(aKey, aValue)
    if (idx == 1) *stop = YES;
    XCTAssertNotEqual(idx, 2U);
    ++idx;
  }];
  [dict release];
}

- (void)testEquality {
  const uint32_t kKeys1[] = { 1U, 2U, 3U, 4U };
  const uint32_t kKeys2[] = { 2U, 1U, 4U };
  const int64_t kValues1[] = { 400, 401, 402 };
  const int64_t kValues2[] = { 400, 403, 402 };
  const int64_t kValues3[] = { 400, 401, 402, 403 };
  GPBUInt32Int64Dictionary *dict1 =
      [[GPBUInt32Int64Dictionary alloc] initWithValues:kValues1
                                               forKeys:kKeys1
                                                 count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1);
  GPBUInt32Int64Dictionary *dict1prime =
      [[GPBUInt32Int64Dictionary alloc] initWithValues:kValues1
                                               forKeys:kKeys1
                                                 count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1prime);
  GPBUInt32Int64Dictionary *dict2 =
      [[GPBUInt32Int64Dictionary alloc] initWithValues:kValues2
                                               forKeys:kKeys1
                                                 count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  GPBUInt32Int64Dictionary *dict3 =
      [[GPBUInt32Int64Dictionary alloc] initWithValues:kValues1
                                               forKeys:kKeys2
                                                 count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict3);
  GPBUInt32Int64Dictionary *dict4 =
      [[GPBUInt32Int64Dictionary alloc] initWithValues:kValues3
                                               forKeys:kKeys1
                                                 count:GPBARRAYSIZE(kValues3)];
  XCTAssertNotNil(dict4);

  // 1/1Prime should be different objects, but equal.
  XCTAssertNotEqual(dict1, dict1prime);
  XCTAssertEqualObjects(dict1, dict1prime);
  // Equal, so they must have same hash.
  XCTAssertEqual([dict1 hash], [dict1prime hash]);

  // 2 is save keys, different values; not equal.
  XCTAssertNotEqualObjects(dict1, dict2);

  // 3 is different keys, samae values; not equal.
  XCTAssertNotEqualObjects(dict1, dict3);

  // 4 extra pair; not equal
  XCTAssertNotEqualObjects(dict1, dict4);

  [dict1 release];
  [dict1prime release];
  [dict2 release];
  [dict3 release];
  [dict4 release];
}

- (void)testCopy {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int64_t kValues[] = { 400, 401, 402, 403 };
  GPBUInt32Int64Dictionary *dict =
      [[GPBUInt32Int64Dictionary alloc] initWithValues:kValues
                                               forKeys:kKeys
                                                 count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32Int64Dictionary *dict2 = [dict copy];
  XCTAssertNotNil(dict2);

  // Should be new object but equal.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  XCTAssertTrue([dict2 isKindOfClass:[GPBUInt32Int64Dictionary class]]);

  [dict2 release];
  [dict release];
}

- (void)testDictionaryFromDictionary {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int64_t kValues[] = { 400, 401, 402, 403 };
  GPBUInt32Int64Dictionary *dict =
      [[GPBUInt32Int64Dictionary alloc] initWithValues:kValues
                                               forKeys:kKeys
                                                 count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32Int64Dictionary *dict2 =
      [GPBUInt32Int64Dictionary dictionaryWithDictionary:dict];
  XCTAssertNotNil(dict2);

  // Should be new pointer, but equal objects.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  [dict release];
}

- (void)testAdds {
  GPBUInt32Int64Dictionary *dict = [GPBUInt32Int64Dictionary dictionary];
  XCTAssertNotNil(dict);

  XCTAssertEqual(dict.count, 0U);
  [dict setValue:400 forKey:1U];
  XCTAssertEqual(dict.count, 1U);

  const uint32_t kKeys[] = { 2U, 3U, 4U };
  const int64_t kValues[] = { 401, 402, 403 };
  GPBUInt32Int64Dictionary *dict2 =
      [[GPBUInt32Int64Dictionary alloc] initWithValues:kValues
                                               forKeys:kKeys
                                                 count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);

  int64_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 400);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 401);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 402);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 403);
  [dict2 release];
}

- (void)testRemove {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int64_t kValues[] = { 400, 401, 402, 403 };
  GPBUInt32Int64Dictionary *dict =
      [[GPBUInt32Int64Dictionary alloc] initWithValues:kValues
                                        forKeys:kKeys
                                          count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);

  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  int64_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 400);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 402);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 403);

  // Remove again does nothing.
  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 400);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 402);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 403);

  [dict removeValueForKey:4U];
  XCTAssertEqual(dict.count, 2U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 400);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 402);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  [dict removeAll];
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertFalse([dict valueForKey:3U value:NULL]);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);
  [dict release];
}

- (void)testInplaceMutation {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int64_t kValues[] = { 400, 401, 402, 403 };
  GPBUInt32Int64Dictionary *dict =
      [[GPBUInt32Int64Dictionary alloc] initWithValues:kValues
                                        forKeys:kKeys
                                          count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);
  int64_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 400);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 401);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 402);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 403);

  [dict setValue:403 forKey:1U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 403);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 401);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 402);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 403);

  [dict setValue:401 forKey:4U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 403);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 401);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 402);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 401);

  const uint32_t kKeys2[] = { 2U, 3U };
  const int64_t kValues2[] = { 402, 400 };
  GPBUInt32Int64Dictionary *dict2 =
      [[GPBUInt32Int64Dictionary alloc] initWithValues:kValues2
                                               forKeys:kKeys2
                                                 count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 403);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 402);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 400);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 401);

  [dict2 release];
  [dict release];
}

@end

#pragma mark - UInt32 -> Bool

@interface GPBUInt32BoolDictionaryTests : XCTestCase
@end

@implementation GPBUInt32BoolDictionaryTests

- (void)testEmpty {
  GPBUInt32BoolDictionary *dict = [[GPBUInt32BoolDictionary alloc] init];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, BOOL aValue, BOOL *stop) {
    #pragma unused(aKey, aValue, stop)
    XCTFail(@"Shouldn't get here!");
  }];
  [dict release];
}

- (void)testOne {
  GPBUInt32BoolDictionary *dict = [GPBUInt32BoolDictionary dictionaryWithValue:YES forKey:1U];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 1U);
  BOOL value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, YES);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, BOOL aValue, BOOL *stop) {
    XCTAssertEqual(aKey, 1U);
    XCTAssertEqual(aValue, YES);
    XCTAssertNotEqual(stop, NULL);
  }];
}

- (void)testBasics {
  const uint32_t kKeys[] = { 1U, 2U, 3U };
  const BOOL kValues[] = { YES, YES, NO };
  GPBUInt32BoolDictionary *dict =
      [[GPBUInt32BoolDictionary alloc] initWithValues:kValues
                                              forKeys:kKeys
                                                count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 3U);
  BOOL value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, YES);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, YES);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, NO);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  __block NSUInteger idx = 0;
  uint32_t *seenKeys = malloc(3 * sizeof(uint32_t));
  BOOL *seenValues = malloc(3 * sizeof(BOOL));
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, BOOL aValue, BOOL *stop) {
    XCTAssertLessThan(idx, 3U);
    seenKeys[idx] = aKey;
    seenValues[idx] = aValue;
    XCTAssertNotEqual(stop, NULL);
    ++idx;
  }];
  for (int i = 0; i < 3; ++i) {
    BOOL foundKey = NO;
    for (int j = 0; (j < 3) && !foundKey; ++j) {
      if (kKeys[i] == seenKeys[j]) {
        foundKey = YES;
        XCTAssertEqual(kValues[i], seenValues[j], @"i = %d, j = %d", i, j);
      }
    }
    XCTAssertTrue(foundKey, @"i = %d", i);
  }
  free(seenKeys);
  free(seenValues);

  // Stopping the enumeration.
  idx = 0;
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, BOOL aValue, BOOL *stop) {
    #pragma unused(aKey, aValue)
    if (idx == 1) *stop = YES;
    XCTAssertNotEqual(idx, 2U);
    ++idx;
  }];
  [dict release];
}

- (void)testEquality {
  const uint32_t kKeys1[] = { 1U, 2U, 3U, 4U };
  const uint32_t kKeys2[] = { 2U, 1U, 4U };
  const BOOL kValues1[] = { YES, YES, NO };
  const BOOL kValues2[] = { YES, NO, NO };
  const BOOL kValues3[] = { YES, YES, NO, NO };
  GPBUInt32BoolDictionary *dict1 =
      [[GPBUInt32BoolDictionary alloc] initWithValues:kValues1
                                              forKeys:kKeys1
                                                count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1);
  GPBUInt32BoolDictionary *dict1prime =
      [[GPBUInt32BoolDictionary alloc] initWithValues:kValues1
                                              forKeys:kKeys1
                                                count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1prime);
  GPBUInt32BoolDictionary *dict2 =
      [[GPBUInt32BoolDictionary alloc] initWithValues:kValues2
                                              forKeys:kKeys1
                                                count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  GPBUInt32BoolDictionary *dict3 =
      [[GPBUInt32BoolDictionary alloc] initWithValues:kValues1
                                              forKeys:kKeys2
                                                count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict3);
  GPBUInt32BoolDictionary *dict4 =
      [[GPBUInt32BoolDictionary alloc] initWithValues:kValues3
                                              forKeys:kKeys1
                                                count:GPBARRAYSIZE(kValues3)];
  XCTAssertNotNil(dict4);

  // 1/1Prime should be different objects, but equal.
  XCTAssertNotEqual(dict1, dict1prime);
  XCTAssertEqualObjects(dict1, dict1prime);
  // Equal, so they must have same hash.
  XCTAssertEqual([dict1 hash], [dict1prime hash]);

  // 2 is save keys, different values; not equal.
  XCTAssertNotEqualObjects(dict1, dict2);

  // 3 is different keys, samae values; not equal.
  XCTAssertNotEqualObjects(dict1, dict3);

  // 4 extra pair; not equal
  XCTAssertNotEqualObjects(dict1, dict4);

  [dict1 release];
  [dict1prime release];
  [dict2 release];
  [dict3 release];
  [dict4 release];
}

- (void)testCopy {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const BOOL kValues[] = { YES, YES, NO, NO };
  GPBUInt32BoolDictionary *dict =
      [[GPBUInt32BoolDictionary alloc] initWithValues:kValues
                                              forKeys:kKeys
                                                count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32BoolDictionary *dict2 = [dict copy];
  XCTAssertNotNil(dict2);

  // Should be new object but equal.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  XCTAssertTrue([dict2 isKindOfClass:[GPBUInt32BoolDictionary class]]);

  [dict2 release];
  [dict release];
}

- (void)testDictionaryFromDictionary {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const BOOL kValues[] = { YES, YES, NO, NO };
  GPBUInt32BoolDictionary *dict =
      [[GPBUInt32BoolDictionary alloc] initWithValues:kValues
                                              forKeys:kKeys
                                                count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32BoolDictionary *dict2 =
      [GPBUInt32BoolDictionary dictionaryWithDictionary:dict];
  XCTAssertNotNil(dict2);

  // Should be new pointer, but equal objects.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  [dict release];
}

- (void)testAdds {
  GPBUInt32BoolDictionary *dict = [GPBUInt32BoolDictionary dictionary];
  XCTAssertNotNil(dict);

  XCTAssertEqual(dict.count, 0U);
  [dict setValue:YES forKey:1U];
  XCTAssertEqual(dict.count, 1U);

  const uint32_t kKeys[] = { 2U, 3U, 4U };
  const BOOL kValues[] = { YES, NO, NO };
  GPBUInt32BoolDictionary *dict2 =
      [[GPBUInt32BoolDictionary alloc] initWithValues:kValues
                                              forKeys:kKeys
                                                count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);

  BOOL value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, YES);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, YES);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, NO);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, NO);
  [dict2 release];
}

- (void)testRemove {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const BOOL kValues[] = { YES, YES, NO, NO };
  GPBUInt32BoolDictionary *dict =
      [[GPBUInt32BoolDictionary alloc] initWithValues:kValues
                                       forKeys:kKeys
                                         count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);

  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  BOOL value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, YES);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, NO);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, NO);

  // Remove again does nothing.
  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, YES);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, NO);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, NO);

  [dict removeValueForKey:4U];
  XCTAssertEqual(dict.count, 2U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, YES);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, NO);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  [dict removeAll];
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertFalse([dict valueForKey:3U value:NULL]);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);
  [dict release];
}

- (void)testInplaceMutation {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const BOOL kValues[] = { YES, YES, NO, NO };
  GPBUInt32BoolDictionary *dict =
      [[GPBUInt32BoolDictionary alloc] initWithValues:kValues
                                       forKeys:kKeys
                                         count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);
  BOOL value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, YES);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, YES);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, NO);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, NO);

  [dict setValue:NO forKey:1U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, NO);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, YES);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, NO);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, NO);

  [dict setValue:YES forKey:4U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, NO);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, YES);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, NO);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, YES);

  const uint32_t kKeys2[] = { 2U, 3U };
  const BOOL kValues2[] = { NO, YES };
  GPBUInt32BoolDictionary *dict2 =
      [[GPBUInt32BoolDictionary alloc] initWithValues:kValues2
                                              forKeys:kKeys2
                                                count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, NO);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, NO);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, YES);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, YES);

  [dict2 release];
  [dict release];
}

@end

#pragma mark - UInt32 -> Float

@interface GPBUInt32FloatDictionaryTests : XCTestCase
@end

@implementation GPBUInt32FloatDictionaryTests

- (void)testEmpty {
  GPBUInt32FloatDictionary *dict = [[GPBUInt32FloatDictionary alloc] init];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, float aValue, BOOL *stop) {
    #pragma unused(aKey, aValue, stop)
    XCTFail(@"Shouldn't get here!");
  }];
  [dict release];
}

- (void)testOne {
  GPBUInt32FloatDictionary *dict = [GPBUInt32FloatDictionary dictionaryWithValue:500.f forKey:1U];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 1U);
  float value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 500.f);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, float aValue, BOOL *stop) {
    XCTAssertEqual(aKey, 1U);
    XCTAssertEqual(aValue, 500.f);
    XCTAssertNotEqual(stop, NULL);
  }];
}

- (void)testBasics {
  const uint32_t kKeys[] = { 1U, 2U, 3U };
  const float kValues[] = { 500.f, 501.f, 502.f };
  GPBUInt32FloatDictionary *dict =
      [[GPBUInt32FloatDictionary alloc] initWithValues:kValues
                                               forKeys:kKeys
                                                 count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 3U);
  float value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 500.f);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 501.f);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 502.f);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  __block NSUInteger idx = 0;
  uint32_t *seenKeys = malloc(3 * sizeof(uint32_t));
  float *seenValues = malloc(3 * sizeof(float));
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, float aValue, BOOL *stop) {
    XCTAssertLessThan(idx, 3U);
    seenKeys[idx] = aKey;
    seenValues[idx] = aValue;
    XCTAssertNotEqual(stop, NULL);
    ++idx;
  }];
  for (int i = 0; i < 3; ++i) {
    BOOL foundKey = NO;
    for (int j = 0; (j < 3) && !foundKey; ++j) {
      if (kKeys[i] == seenKeys[j]) {
        foundKey = YES;
        XCTAssertEqual(kValues[i], seenValues[j], @"i = %d, j = %d", i, j);
      }
    }
    XCTAssertTrue(foundKey, @"i = %d", i);
  }
  free(seenKeys);
  free(seenValues);

  // Stopping the enumeration.
  idx = 0;
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, float aValue, BOOL *stop) {
    #pragma unused(aKey, aValue)
    if (idx == 1) *stop = YES;
    XCTAssertNotEqual(idx, 2U);
    ++idx;
  }];
  [dict release];
}

- (void)testEquality {
  const uint32_t kKeys1[] = { 1U, 2U, 3U, 4U };
  const uint32_t kKeys2[] = { 2U, 1U, 4U };
  const float kValues1[] = { 500.f, 501.f, 502.f };
  const float kValues2[] = { 500.f, 503.f, 502.f };
  const float kValues3[] = { 500.f, 501.f, 502.f, 503.f };
  GPBUInt32FloatDictionary *dict1 =
      [[GPBUInt32FloatDictionary alloc] initWithValues:kValues1
                                               forKeys:kKeys1
                                                 count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1);
  GPBUInt32FloatDictionary *dict1prime =
      [[GPBUInt32FloatDictionary alloc] initWithValues:kValues1
                                               forKeys:kKeys1
                                                 count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1prime);
  GPBUInt32FloatDictionary *dict2 =
      [[GPBUInt32FloatDictionary alloc] initWithValues:kValues2
                                               forKeys:kKeys1
                                                 count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  GPBUInt32FloatDictionary *dict3 =
      [[GPBUInt32FloatDictionary alloc] initWithValues:kValues1
                                               forKeys:kKeys2
                                                 count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict3);
  GPBUInt32FloatDictionary *dict4 =
      [[GPBUInt32FloatDictionary alloc] initWithValues:kValues3
                                               forKeys:kKeys1
                                                 count:GPBARRAYSIZE(kValues3)];
  XCTAssertNotNil(dict4);

  // 1/1Prime should be different objects, but equal.
  XCTAssertNotEqual(dict1, dict1prime);
  XCTAssertEqualObjects(dict1, dict1prime);
  // Equal, so they must have same hash.
  XCTAssertEqual([dict1 hash], [dict1prime hash]);

  // 2 is save keys, different values; not equal.
  XCTAssertNotEqualObjects(dict1, dict2);

  // 3 is different keys, samae values; not equal.
  XCTAssertNotEqualObjects(dict1, dict3);

  // 4 extra pair; not equal
  XCTAssertNotEqualObjects(dict1, dict4);

  [dict1 release];
  [dict1prime release];
  [dict2 release];
  [dict3 release];
  [dict4 release];
}

- (void)testCopy {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const float kValues[] = { 500.f, 501.f, 502.f, 503.f };
  GPBUInt32FloatDictionary *dict =
      [[GPBUInt32FloatDictionary alloc] initWithValues:kValues
                                               forKeys:kKeys
                                                 count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32FloatDictionary *dict2 = [dict copy];
  XCTAssertNotNil(dict2);

  // Should be new object but equal.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  XCTAssertTrue([dict2 isKindOfClass:[GPBUInt32FloatDictionary class]]);

  [dict2 release];
  [dict release];
}

- (void)testDictionaryFromDictionary {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const float kValues[] = { 500.f, 501.f, 502.f, 503.f };
  GPBUInt32FloatDictionary *dict =
      [[GPBUInt32FloatDictionary alloc] initWithValues:kValues
                                               forKeys:kKeys
                                                 count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32FloatDictionary *dict2 =
      [GPBUInt32FloatDictionary dictionaryWithDictionary:dict];
  XCTAssertNotNil(dict2);

  // Should be new pointer, but equal objects.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  [dict release];
}

- (void)testAdds {
  GPBUInt32FloatDictionary *dict = [GPBUInt32FloatDictionary dictionary];
  XCTAssertNotNil(dict);

  XCTAssertEqual(dict.count, 0U);
  [dict setValue:500.f forKey:1U];
  XCTAssertEqual(dict.count, 1U);

  const uint32_t kKeys[] = { 2U, 3U, 4U };
  const float kValues[] = { 501.f, 502.f, 503.f };
  GPBUInt32FloatDictionary *dict2 =
      [[GPBUInt32FloatDictionary alloc] initWithValues:kValues
                                               forKeys:kKeys
                                                 count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);

  float value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 500.f);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 501.f);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 502.f);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 503.f);
  [dict2 release];
}

- (void)testRemove {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const float kValues[] = { 500.f, 501.f, 502.f, 503.f };
  GPBUInt32FloatDictionary *dict =
      [[GPBUInt32FloatDictionary alloc] initWithValues:kValues
                                        forKeys:kKeys
                                          count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);

  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  float value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 500.f);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 502.f);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 503.f);

  // Remove again does nothing.
  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 500.f);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 502.f);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 503.f);

  [dict removeValueForKey:4U];
  XCTAssertEqual(dict.count, 2U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 500.f);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 502.f);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  [dict removeAll];
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertFalse([dict valueForKey:3U value:NULL]);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);
  [dict release];
}

- (void)testInplaceMutation {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const float kValues[] = { 500.f, 501.f, 502.f, 503.f };
  GPBUInt32FloatDictionary *dict =
      [[GPBUInt32FloatDictionary alloc] initWithValues:kValues
                                        forKeys:kKeys
                                          count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);
  float value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 500.f);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 501.f);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 502.f);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 503.f);

  [dict setValue:503.f forKey:1U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 503.f);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 501.f);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 502.f);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 503.f);

  [dict setValue:501.f forKey:4U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 503.f);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 501.f);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 502.f);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 501.f);

  const uint32_t kKeys2[] = { 2U, 3U };
  const float kValues2[] = { 502.f, 500.f };
  GPBUInt32FloatDictionary *dict2 =
      [[GPBUInt32FloatDictionary alloc] initWithValues:kValues2
                                               forKeys:kKeys2
                                                 count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 503.f);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 502.f);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 500.f);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 501.f);

  [dict2 release];
  [dict release];
}

@end

#pragma mark - UInt32 -> Double

@interface GPBUInt32DoubleDictionaryTests : XCTestCase
@end

@implementation GPBUInt32DoubleDictionaryTests

- (void)testEmpty {
  GPBUInt32DoubleDictionary *dict = [[GPBUInt32DoubleDictionary alloc] init];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, double aValue, BOOL *stop) {
    #pragma unused(aKey, aValue, stop)
    XCTFail(@"Shouldn't get here!");
  }];
  [dict release];
}

- (void)testOne {
  GPBUInt32DoubleDictionary *dict = [GPBUInt32DoubleDictionary dictionaryWithValue:600. forKey:1U];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 1U);
  double value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 600.);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, double aValue, BOOL *stop) {
    XCTAssertEqual(aKey, 1U);
    XCTAssertEqual(aValue, 600.);
    XCTAssertNotEqual(stop, NULL);
  }];
}

- (void)testBasics {
  const uint32_t kKeys[] = { 1U, 2U, 3U };
  const double kValues[] = { 600., 601., 602. };
  GPBUInt32DoubleDictionary *dict =
      [[GPBUInt32DoubleDictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 3U);
  double value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 600.);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 601.);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 602.);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  __block NSUInteger idx = 0;
  uint32_t *seenKeys = malloc(3 * sizeof(uint32_t));
  double *seenValues = malloc(3 * sizeof(double));
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, double aValue, BOOL *stop) {
    XCTAssertLessThan(idx, 3U);
    seenKeys[idx] = aKey;
    seenValues[idx] = aValue;
    XCTAssertNotEqual(stop, NULL);
    ++idx;
  }];
  for (int i = 0; i < 3; ++i) {
    BOOL foundKey = NO;
    for (int j = 0; (j < 3) && !foundKey; ++j) {
      if (kKeys[i] == seenKeys[j]) {
        foundKey = YES;
        XCTAssertEqual(kValues[i], seenValues[j], @"i = %d, j = %d", i, j);
      }
    }
    XCTAssertTrue(foundKey, @"i = %d", i);
  }
  free(seenKeys);
  free(seenValues);

  // Stopping the enumeration.
  idx = 0;
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, double aValue, BOOL *stop) {
    #pragma unused(aKey, aValue)
    if (idx == 1) *stop = YES;
    XCTAssertNotEqual(idx, 2U);
    ++idx;
  }];
  [dict release];
}

- (void)testEquality {
  const uint32_t kKeys1[] = { 1U, 2U, 3U, 4U };
  const uint32_t kKeys2[] = { 2U, 1U, 4U };
  const double kValues1[] = { 600., 601., 602. };
  const double kValues2[] = { 600., 603., 602. };
  const double kValues3[] = { 600., 601., 602., 603. };
  GPBUInt32DoubleDictionary *dict1 =
      [[GPBUInt32DoubleDictionary alloc] initWithValues:kValues1
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1);
  GPBUInt32DoubleDictionary *dict1prime =
      [[GPBUInt32DoubleDictionary alloc] initWithValues:kValues1
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1prime);
  GPBUInt32DoubleDictionary *dict2 =
      [[GPBUInt32DoubleDictionary alloc] initWithValues:kValues2
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  GPBUInt32DoubleDictionary *dict3 =
      [[GPBUInt32DoubleDictionary alloc] initWithValues:kValues1
                                                forKeys:kKeys2
                                                  count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict3);
  GPBUInt32DoubleDictionary *dict4 =
      [[GPBUInt32DoubleDictionary alloc] initWithValues:kValues3
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues3)];
  XCTAssertNotNil(dict4);

  // 1/1Prime should be different objects, but equal.
  XCTAssertNotEqual(dict1, dict1prime);
  XCTAssertEqualObjects(dict1, dict1prime);
  // Equal, so they must have same hash.
  XCTAssertEqual([dict1 hash], [dict1prime hash]);

  // 2 is save keys, different values; not equal.
  XCTAssertNotEqualObjects(dict1, dict2);

  // 3 is different keys, samae values; not equal.
  XCTAssertNotEqualObjects(dict1, dict3);

  // 4 extra pair; not equal
  XCTAssertNotEqualObjects(dict1, dict4);

  [dict1 release];
  [dict1prime release];
  [dict2 release];
  [dict3 release];
  [dict4 release];
}

- (void)testCopy {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const double kValues[] = { 600., 601., 602., 603. };
  GPBUInt32DoubleDictionary *dict =
      [[GPBUInt32DoubleDictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32DoubleDictionary *dict2 = [dict copy];
  XCTAssertNotNil(dict2);

  // Should be new object but equal.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  XCTAssertTrue([dict2 isKindOfClass:[GPBUInt32DoubleDictionary class]]);

  [dict2 release];
  [dict release];
}

- (void)testDictionaryFromDictionary {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const double kValues[] = { 600., 601., 602., 603. };
  GPBUInt32DoubleDictionary *dict =
      [[GPBUInt32DoubleDictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32DoubleDictionary *dict2 =
      [GPBUInt32DoubleDictionary dictionaryWithDictionary:dict];
  XCTAssertNotNil(dict2);

  // Should be new pointer, but equal objects.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  [dict release];
}

- (void)testAdds {
  GPBUInt32DoubleDictionary *dict = [GPBUInt32DoubleDictionary dictionary];
  XCTAssertNotNil(dict);

  XCTAssertEqual(dict.count, 0U);
  [dict setValue:600. forKey:1U];
  XCTAssertEqual(dict.count, 1U);

  const uint32_t kKeys[] = { 2U, 3U, 4U };
  const double kValues[] = { 601., 602., 603. };
  GPBUInt32DoubleDictionary *dict2 =
      [[GPBUInt32DoubleDictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);

  double value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 600.);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 601.);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 602.);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 603.);
  [dict2 release];
}

- (void)testRemove {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const double kValues[] = { 600., 601., 602., 603. };
  GPBUInt32DoubleDictionary *dict =
      [[GPBUInt32DoubleDictionary alloc] initWithValues:kValues
                                         forKeys:kKeys
                                           count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);

  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  double value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 600.);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 602.);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 603.);

  // Remove again does nothing.
  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 600.);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 602.);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 603.);

  [dict removeValueForKey:4U];
  XCTAssertEqual(dict.count, 2U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 600.);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 602.);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  [dict removeAll];
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertFalse([dict valueForKey:3U value:NULL]);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);
  [dict release];
}

- (void)testInplaceMutation {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const double kValues[] = { 600., 601., 602., 603. };
  GPBUInt32DoubleDictionary *dict =
      [[GPBUInt32DoubleDictionary alloc] initWithValues:kValues
                                         forKeys:kKeys
                                           count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);
  double value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 600.);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 601.);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 602.);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 603.);

  [dict setValue:603. forKey:1U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 603.);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 601.);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 602.);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 603.);

  [dict setValue:601. forKey:4U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 603.);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 601.);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 602.);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 601.);

  const uint32_t kKeys2[] = { 2U, 3U };
  const double kValues2[] = { 602., 600. };
  GPBUInt32DoubleDictionary *dict2 =
      [[GPBUInt32DoubleDictionary alloc] initWithValues:kValues2
                                                forKeys:kKeys2
                                                  count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 603.);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 602.);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 600.);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 601.);

  [dict2 release];
  [dict release];
}

@end

#pragma mark - UInt32 -> Enum

@interface GPBUInt32EnumDictionaryTests : XCTestCase
@end

@implementation GPBUInt32EnumDictionaryTests

- (void)testEmpty {
  GPBUInt32EnumDictionary *dict = [[GPBUInt32EnumDictionary alloc] init];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, int32_t aValue, BOOL *stop) {
    #pragma unused(aKey, aValue, stop)
    XCTFail(@"Shouldn't get here!");
  }];
  [dict release];
}

- (void)testOne {
  GPBUInt32EnumDictionary *dict = [GPBUInt32EnumDictionary dictionaryWithValue:700 forKey:1U];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 1U);
  int32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 700);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, int32_t aValue, BOOL *stop) {
    XCTAssertEqual(aKey, 1U);
    XCTAssertEqual(aValue, 700);
    XCTAssertNotEqual(stop, NULL);
  }];
}

- (void)testBasics {
  const uint32_t kKeys[] = { 1U, 2U, 3U };
  const int32_t kValues[] = { 700, 701, 702 };
  GPBUInt32EnumDictionary *dict =
      [[GPBUInt32EnumDictionary alloc] initWithValues:kValues
                                              forKeys:kKeys
                                                count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 3U);
  int32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 700);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 701);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  __block NSUInteger idx = 0;
  uint32_t *seenKeys = malloc(3 * sizeof(uint32_t));
  int32_t *seenValues = malloc(3 * sizeof(int32_t));
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, int32_t aValue, BOOL *stop) {
    XCTAssertLessThan(idx, 3U);
    seenKeys[idx] = aKey;
    seenValues[idx] = aValue;
    XCTAssertNotEqual(stop, NULL);
    ++idx;
  }];
  for (int i = 0; i < 3; ++i) {
    BOOL foundKey = NO;
    for (int j = 0; (j < 3) && !foundKey; ++j) {
      if (kKeys[i] == seenKeys[j]) {
        foundKey = YES;
        XCTAssertEqual(kValues[i], seenValues[j], @"i = %d, j = %d", i, j);
      }
    }
    XCTAssertTrue(foundKey, @"i = %d", i);
  }
  free(seenKeys);
  free(seenValues);

  // Stopping the enumeration.
  idx = 0;
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, int32_t aValue, BOOL *stop) {
    #pragma unused(aKey, aValue)
    if (idx == 1) *stop = YES;
    XCTAssertNotEqual(idx, 2U);
    ++idx;
  }];
  [dict release];
}

- (void)testEquality {
  const uint32_t kKeys1[] = { 1U, 2U, 3U, 4U };
  const uint32_t kKeys2[] = { 2U, 1U, 4U };
  const int32_t kValues1[] = { 700, 701, 702 };
  const int32_t kValues2[] = { 700, 703, 702 };
  const int32_t kValues3[] = { 700, 701, 702, 703 };
  GPBUInt32EnumDictionary *dict1 =
      [[GPBUInt32EnumDictionary alloc] initWithValues:kValues1
                                              forKeys:kKeys1
                                                count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1);
  GPBUInt32EnumDictionary *dict1prime =
      [[GPBUInt32EnumDictionary alloc] initWithValues:kValues1
                                              forKeys:kKeys1
                                                count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1prime);
  GPBUInt32EnumDictionary *dict2 =
      [[GPBUInt32EnumDictionary alloc] initWithValues:kValues2
                                              forKeys:kKeys1
                                                count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  GPBUInt32EnumDictionary *dict3 =
      [[GPBUInt32EnumDictionary alloc] initWithValues:kValues1
                                              forKeys:kKeys2
                                                count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict3);
  GPBUInt32EnumDictionary *dict4 =
      [[GPBUInt32EnumDictionary alloc] initWithValues:kValues3
                                              forKeys:kKeys1
                                                count:GPBARRAYSIZE(kValues3)];
  XCTAssertNotNil(dict4);

  // 1/1Prime should be different objects, but equal.
  XCTAssertNotEqual(dict1, dict1prime);
  XCTAssertEqualObjects(dict1, dict1prime);
  // Equal, so they must have same hash.
  XCTAssertEqual([dict1 hash], [dict1prime hash]);

  // 2 is save keys, different values; not equal.
  XCTAssertNotEqualObjects(dict1, dict2);

  // 3 is different keys, samae values; not equal.
  XCTAssertNotEqualObjects(dict1, dict3);

  // 4 extra pair; not equal
  XCTAssertNotEqualObjects(dict1, dict4);

  [dict1 release];
  [dict1prime release];
  [dict2 release];
  [dict3 release];
  [dict4 release];
}

- (void)testCopy {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int32_t kValues[] = { 700, 701, 702, 703 };
  GPBUInt32EnumDictionary *dict =
      [[GPBUInt32EnumDictionary alloc] initWithValues:kValues
                                              forKeys:kKeys
                                                count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32EnumDictionary *dict2 = [dict copy];
  XCTAssertNotNil(dict2);

  // Should be new object but equal.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  XCTAssertTrue([dict2 isKindOfClass:[GPBUInt32EnumDictionary class]]);

  [dict2 release];
  [dict release];
}

- (void)testDictionaryFromDictionary {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int32_t kValues[] = { 700, 701, 702, 703 };
  GPBUInt32EnumDictionary *dict =
      [[GPBUInt32EnumDictionary alloc] initWithValues:kValues
                                              forKeys:kKeys
                                                count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32EnumDictionary *dict2 =
      [GPBUInt32EnumDictionary dictionaryWithDictionary:dict];
  XCTAssertNotNil(dict2);

  // Should be new pointer, but equal objects.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  [dict release];
}

- (void)testAdds {
  GPBUInt32EnumDictionary *dict = [GPBUInt32EnumDictionary dictionary];
  XCTAssertNotNil(dict);

  XCTAssertEqual(dict.count, 0U);
  [dict setValue:700 forKey:1U];
  XCTAssertEqual(dict.count, 1U);

  const uint32_t kKeys[] = { 2U, 3U, 4U };
  const int32_t kValues[] = { 701, 702, 703 };
  GPBUInt32EnumDictionary *dict2 =
      [[GPBUInt32EnumDictionary alloc] initWithValues:kValues
                                              forKeys:kKeys
                                                count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict2);
  [dict addRawEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);

  int32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 700);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 701);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 703);
  [dict2 release];
}

- (void)testRemove {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int32_t kValues[] = { 700, 701, 702, 703 };
  GPBUInt32EnumDictionary *dict =
      [[GPBUInt32EnumDictionary alloc] initWithValues:kValues
                                       forKeys:kKeys
                                         count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);

  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  int32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 700);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 703);

  // Remove again does nothing.
  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 700);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 703);

  [dict removeValueForKey:4U];
  XCTAssertEqual(dict.count, 2U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 700);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  [dict removeAll];
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertFalse([dict valueForKey:3U value:NULL]);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);
  [dict release];
}

- (void)testInplaceMutation {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int32_t kValues[] = { 700, 701, 702, 703 };
  GPBUInt32EnumDictionary *dict =
      [[GPBUInt32EnumDictionary alloc] initWithValues:kValues
                                       forKeys:kKeys
                                         count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);
  int32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 700);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 701);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 703);

  [dict setValue:703 forKey:1U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 703);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 701);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 703);

  [dict setValue:701 forKey:4U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 703);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 701);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 701);

  const uint32_t kKeys2[] = { 2U, 3U };
  const int32_t kValues2[] = { 702, 700 };
  GPBUInt32EnumDictionary *dict2 =
      [[GPBUInt32EnumDictionary alloc] initWithValues:kValues2
                                              forKeys:kKeys2
                                                count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  [dict addRawEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 703);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 700);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 701);

  [dict2 release];
  [dict release];
}

@end

#pragma mark - UInt32 -> Enum (Unknown Enums)

@interface GPBUInt32EnumDictionaryUnknownEnumTests : XCTestCase
@end

@implementation GPBUInt32EnumDictionaryUnknownEnumTests

- (void)testRawBasics {
  const uint32_t kKeys[] = { 1U, 2U, 3U };
  const int32_t kValues[] = { 700, 801, 702 };
  GPBUInt32EnumDictionary *dict =
      [[GPBUInt32EnumDictionary alloc] initWithValidationFunction:TestingEnum_IsValidValue
                                                        rawValues:kValues
                                                          forKeys:kKeys
                                                            count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 3U);
  XCTAssertTrue(dict.validationFunc == TestingEnum_IsValidValue);  // Pointer comparison
  int32_t value;
  XCTAssertTrue([dict valueForKey:1U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:1U rawValue:&value]);
  XCTAssertEqual(value, 700);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, kGPBUnrecognizedEnumeratorValue);
  XCTAssertTrue([dict valueForKey:2U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:2U rawValue:&value]);
  XCTAssertEqual(value, 801);
  XCTAssertTrue([dict valueForKey:3U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:3U rawValue:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertFalse([dict valueForKey:4U rawValue:NULL]);

  __block NSUInteger idx = 0;
  uint32_t *seenKeys = malloc(3 * sizeof(uint32_t));
  int32_t *seenValues = malloc(3 * sizeof(int32_t));
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, int32_t aValue, BOOL *stop) {
    XCTAssertLessThan(idx, 3U);
    seenKeys[idx] = aKey;
    seenValues[idx] = aValue;
    XCTAssertNotEqual(stop, NULL);
    ++idx;
  }];
  for (int i = 0; i < 3; ++i) {
    BOOL foundKey = NO;
    for (int j = 0; (j < 3) && !foundKey; ++j) {
      if (kKeys[i] == seenKeys[j]) {
        foundKey = YES;
        if (i == 1) {
          XCTAssertEqual(kGPBUnrecognizedEnumeratorValue, seenValues[j], @"i = %d, j = %d", i, j);
        } else {
          XCTAssertEqual(kValues[i], seenValues[j], @"i = %d, j = %d", i, j);
        }
      }
    }
    XCTAssertTrue(foundKey, @"i = %d", i);
  }
  idx = 0;
  [dict enumerateKeysAndRawValuesUsingBlock:^(uint32_t aKey, int32_t aValue, BOOL *stop) {
    XCTAssertLessThan(idx, 3U);
    seenKeys[idx] = aKey;
    seenValues[idx] = aValue;
    XCTAssertNotEqual(stop, NULL);
    ++idx;
  }];
  for (int i = 0; i < 3; ++i) {
    BOOL foundKey = NO;
    for (int j = 0; (j < 3) && !foundKey; ++j) {
      if (kKeys[i] == seenKeys[j]) {
        foundKey = YES;
        XCTAssertEqual(kValues[i], seenValues[j], @"i = %d, j = %d", i, j);
      }
    }
    XCTAssertTrue(foundKey, @"i = %d", i);
  }
  free(seenKeys);
  free(seenValues);

  // Stopping the enumeration.
  idx = 0;
  [dict enumerateKeysAndRawValuesUsingBlock:^(uint32_t aKey, int32_t aValue, BOOL *stop) {
    #pragma unused(aKey, aValue)
    if (idx == 1) *stop = YES;
    XCTAssertNotEqual(idx, 2U);
    ++idx;
  }];
  [dict release];
}

- (void)testEqualityWithUnknowns {
  const uint32_t kKeys1[] = { 1U, 2U, 3U, 4U };
  const uint32_t kKeys2[] = { 2U, 1U, 4U };
  const int32_t kValues1[] = { 700, 801, 702 };  // Unknown
  const int32_t kValues2[] = { 700, 803, 702 };  // Unknown
  const int32_t kValues3[] = { 700, 801, 702, 803 };  // Unknowns
  GPBUInt32EnumDictionary *dict1 =
      [[GPBUInt32EnumDictionary alloc] initWithValidationFunction:TestingEnum_IsValidValue
                                                        rawValues:kValues1
                                                          forKeys:kKeys1
                                                            count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1);
  GPBUInt32EnumDictionary *dict1prime =
      [[GPBUInt32EnumDictionary alloc] initWithValidationFunction:TestingEnum_IsValidValue
                                                        rawValues:kValues1
                                                          forKeys:kKeys1
                                                            count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1prime);
  GPBUInt32EnumDictionary *dict2 =
      [[GPBUInt32EnumDictionary alloc] initWithValidationFunction:TestingEnum_IsValidValue
                                                        rawValues:kValues2
                                                          forKeys:kKeys1
                                                            count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  GPBUInt32EnumDictionary *dict3 =
      [[GPBUInt32EnumDictionary alloc] initWithValidationFunction:TestingEnum_IsValidValue
                                                        rawValues:kValues1
                                                          forKeys:kKeys2
                                                            count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict3);
  GPBUInt32EnumDictionary *dict4 =
      [[GPBUInt32EnumDictionary alloc] initWithValidationFunction:TestingEnum_IsValidValue
                                                        rawValues:kValues3
                                                          forKeys:kKeys1
                                                            count:GPBARRAYSIZE(kValues3)];
  XCTAssertNotNil(dict4);

  // 1/1Prime should be different objects, but equal.
  XCTAssertNotEqual(dict1, dict1prime);
  XCTAssertEqualObjects(dict1, dict1prime);
  // Equal, so they must have same hash.
  XCTAssertEqual([dict1 hash], [dict1prime hash]);

  // 2 is save keys, different values; not equal.
  XCTAssertNotEqualObjects(dict1, dict2);

  // 3 is different keys, samae values; not equal.
  XCTAssertNotEqualObjects(dict1, dict3);

  // 4 extra pair; not equal
  XCTAssertNotEqualObjects(dict1, dict4);

  [dict1 release];
  [dict1prime release];
  [dict2 release];
  [dict3 release];
  [dict4 release];
}

- (void)testCopyWithUnknowns {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int32_t kValues[] = { 700, 801, 702, 803 };  // Unknown
  GPBUInt32EnumDictionary *dict =
      [[GPBUInt32EnumDictionary alloc] initWithValidationFunction:TestingEnum_IsValidValue
                                                        rawValues:kValues
                                                          forKeys:kKeys
                                                            count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32EnumDictionary *dict2 = [dict copy];
  XCTAssertNotNil(dict2);

  // Should be new pointer, but equal objects.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqual(dict.validationFunc, dict2.validationFunc);  // Pointer comparison
  XCTAssertEqualObjects(dict, dict2);

  [dict2 release];
  [dict release];
}

- (void)testDictionaryFromDictionary {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int32_t kValues[] = { 700, 801, 702, 803 };  // Unknowns
  GPBUInt32EnumDictionary *dict =
      [[GPBUInt32EnumDictionary alloc] initWithValidationFunction:TestingEnum_IsValidValue
                                                        rawValues:kValues
                                                          forKeys:kKeys
                                                            count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32EnumDictionary *dict2 =
      [GPBUInt32EnumDictionary dictionaryWithDictionary:dict];
  XCTAssertNotNil(dict2);

  // Should be new pointer, but equal objects.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  XCTAssertEqual(dict.validationFunc, dict2.validationFunc);  // Pointer comparison
  [dict release];
}

- (void)testUnknownAdds {
  GPBUInt32EnumDictionary *dict =
    [GPBUInt32EnumDictionary dictionaryWithValidationFunction:TestingEnum_IsValidValue];
  XCTAssertNotNil(dict);

  XCTAssertEqual(dict.count, 0U);
  XCTAssertThrowsSpecificNamed([dict setValue:801 forKey:2U],  // Unknown
                               NSException, NSInvalidArgumentException);
  XCTAssertEqual(dict.count, 0U);
  [dict setRawValue:801 forKey:2U];  // Unknown
  XCTAssertEqual(dict.count, 1U);

  const uint32_t kKeys[] = { 1U, 3U, 4U };
  const int32_t kValues[] = { 700, 702, 803 };  // Unknown
  GPBUInt32EnumDictionary *dict2 =
      [[GPBUInt32EnumDictionary alloc] initWithValues:kValues
                                              forKeys:kKeys
                                                count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict2);
  [dict addRawEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);

  int32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 700);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, kGPBUnrecognizedEnumeratorValue);
  XCTAssertTrue([dict valueForKey:2U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:2U rawValue:&value]);
  XCTAssertEqual(value, 801);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, kGPBUnrecognizedEnumeratorValue);
  XCTAssertTrue([dict valueForKey:4U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:4U rawValue:&value]);
  XCTAssertEqual(value, 803);
  [dict2 release];
}

- (void)testUnknownRemove {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int32_t kValues[] = { 700, 801, 702, 803 };  // Unknowns
  GPBUInt32EnumDictionary *dict =
      [[GPBUInt32EnumDictionary alloc] initWithValidationFunction:TestingEnum_IsValidValue
                                                        rawValues:kValues
                                                          forKeys:kKeys
                                                            count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);

  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  int32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 700);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertTrue([dict valueForKey:4U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:4U rawValue:&value]);
  XCTAssertEqual(value, 803);

  // Remove again does nothing.
  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 700);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertTrue([dict valueForKey:4U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:4U rawValue:&value]);
  XCTAssertEqual(value, 803);

  [dict removeValueForKey:4U];
  XCTAssertEqual(dict.count, 2U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 700);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);

  [dict removeAll];
  XCTAssertEqual(dict.count, 0U);
  XCTAssertFalse([dict valueForKey:1U value:NULL]);
  XCTAssertFalse([dict valueForKey:2U value:NULL]);
  XCTAssertFalse([dict valueForKey:3U value:NULL]);
  XCTAssertFalse([dict valueForKey:4U value:NULL]);
  [dict release];
}

- (void)testInplaceMutationUnknowns {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int32_t kValues[] = { 700, 801, 702, 803 };  // Unknowns
  GPBUInt32EnumDictionary *dict =
      [[GPBUInt32EnumDictionary alloc] initWithValidationFunction:TestingEnum_IsValidValue
                                                        rawValues:kValues
                                                          forKeys:kKeys
                                                            count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);
  int32_t value;
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 700);
  XCTAssertTrue([dict valueForKey:2U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:2U rawValue:&value]);
  XCTAssertEqual(value, 801);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertTrue([dict valueForKey:4U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:4U rawValue:&value]);
  XCTAssertEqual(value, 803);

  XCTAssertThrowsSpecificNamed([dict setValue:803 forKey:1U],  // Unknown
                               NSException, NSInvalidArgumentException);
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U value:NULL]);
  XCTAssertTrue([dict valueForKey:1U value:&value]);
  XCTAssertEqual(value, 700);
  XCTAssertTrue([dict valueForKey:2U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:2U rawValue:&value]);
  XCTAssertEqual(value, 801);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertTrue([dict valueForKey:4U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:4U rawValue:&value]);
  XCTAssertEqual(value, 803);

  [dict setRawValue:803 forKey:1U];  // Unknown
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:1U rawValue:&value]);
  XCTAssertEqual(value, 803);
  XCTAssertTrue([dict valueForKey:2U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:2U rawValue:&value]);
  XCTAssertEqual(value, 801);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertTrue([dict valueForKey:4U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:4U rawValue:&value]);
  XCTAssertEqual(value, 803);

  [dict setRawValue:700 forKey:4U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:1U rawValue:&value]);
  XCTAssertEqual(value, 803);
  XCTAssertTrue([dict valueForKey:2U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:2U rawValue:&value]);
  XCTAssertEqual(value, 801);
  XCTAssertTrue([dict valueForKey:3U value:NULL]);
  XCTAssertTrue([dict valueForKey:3U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 700);

  const uint32_t kKeys2[] = { 2U, 3U };
  const int32_t kValues2[] = { 702, 801 };  // Unknown
  GPBUInt32EnumDictionary *dict2 =
      [[GPBUInt32EnumDictionary alloc] initWithValidationFunction:TestingEnum_IsValidValue
                                                        rawValues:kValues2
                                                          forKeys:kKeys2
                                                            count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  [dict addRawEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertTrue([dict valueForKey:1U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:1U rawValue:&value]);
  XCTAssertEqual(value, 803);
  XCTAssertTrue([dict valueForKey:2U value:NULL]);
  XCTAssertTrue([dict valueForKey:2U value:&value]);
  XCTAssertEqual(value, 702);
  XCTAssertTrue([dict valueForKey:3U rawValue:NULL]);
  XCTAssertTrue([dict valueForKey:3U rawValue:&value]);
  XCTAssertEqual(value, 801);
  XCTAssertTrue([dict valueForKey:4U value:NULL]);
  XCTAssertTrue([dict valueForKey:4U value:&value]);
  XCTAssertEqual(value, 700);

  [dict2 release];
  [dict release];
}

- (void)testCopyUnknowns {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const int32_t kValues[] = { 700, 801, 702, 803 };
  GPBUInt32EnumDictionary *dict =
      [[GPBUInt32EnumDictionary alloc] initWithValidationFunction:TestingEnum_IsValidValue
                                                        rawValues:kValues
                                                          forKeys:kKeys
                                                            count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32EnumDictionary *dict2 = [dict copy];
  XCTAssertNotNil(dict2);

  // Should be new pointer, but equal objects.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  XCTAssertEqual(dict.validationFunc, dict2.validationFunc);  // Pointer comparison
  XCTAssertTrue([dict2 isKindOfClass:[GPBUInt32EnumDictionary class]]);

  [dict2 release];
  [dict release];
}

@end

#pragma mark - UInt32 -> Object

@interface GPBUInt32ObjectDictionaryTests : XCTestCase
@end

@implementation GPBUInt32ObjectDictionaryTests

- (void)testEmpty {
  GPBUInt32ObjectDictionary *dict = [[GPBUInt32ObjectDictionary alloc] init];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 0U);
  XCTAssertNil([dict valueForKey:1U]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, id aValue, BOOL *stop) {
    #pragma unused(aKey, aValue, stop)
    XCTFail(@"Shouldn't get here!");
  }];
  [dict release];
}

- (void)testOne {
  GPBUInt32ObjectDictionary *dict = [GPBUInt32ObjectDictionary dictionaryWithValue:@"abc" forKey:1U];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 1U);
  XCTAssertEqualObjects([dict valueForKey:1U], @"abc");
  XCTAssertNil([dict valueForKey:2U]);
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, id aValue, BOOL *stop) {
    XCTAssertEqual(aKey, 1U);
    XCTAssertEqualObjects(aValue, @"abc");
    XCTAssertNotEqual(stop, NULL);
  }];
}

- (void)testBasics {
  const uint32_t kKeys[] = { 1U, 2U, 3U };
  const id kValues[] = { @"abc", @"def", @"ghi" };
  GPBUInt32ObjectDictionary *dict =
      [[GPBUInt32ObjectDictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 3U);
  XCTAssertEqualObjects([dict valueForKey:1U], @"abc");
  XCTAssertEqualObjects([dict valueForKey:2U], @"def");
  XCTAssertEqualObjects([dict valueForKey:3U], @"ghi");
  XCTAssertNil([dict valueForKey:4U]);

  __block NSUInteger idx = 0;
  uint32_t *seenKeys = malloc(3 * sizeof(uint32_t));
  id *seenValues = malloc(3 * sizeof(id));
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, id aValue, BOOL *stop) {
    XCTAssertLessThan(idx, 3U);
    seenKeys[idx] = aKey;
    seenValues[idx] = aValue;
    XCTAssertNotEqual(stop, NULL);
    ++idx;
  }];
  for (int i = 0; i < 3; ++i) {
    BOOL foundKey = NO;
    for (int j = 0; (j < 3) && !foundKey; ++j) {
      if (kKeys[i] == seenKeys[j]) {
        foundKey = YES;
        XCTAssertEqualObjects(kValues[i], seenValues[j], @"i = %d, j = %d", i, j);
      }
    }
    XCTAssertTrue(foundKey, @"i = %d", i);
  }
  free(seenKeys);
  free(seenValues);

  // Stopping the enumeration.
  idx = 0;
  [dict enumerateKeysAndValuesUsingBlock:^(uint32_t aKey, id aValue, BOOL *stop) {
    #pragma unused(aKey, aValue)
    if (idx == 1) *stop = YES;
    XCTAssertNotEqual(idx, 2U);
    ++idx;
  }];
  [dict release];
}

- (void)testEquality {
  const uint32_t kKeys1[] = { 1U, 2U, 3U, 4U };
  const uint32_t kKeys2[] = { 2U, 1U, 4U };
  const id kValues1[] = { @"abc", @"def", @"ghi" };
  const id kValues2[] = { @"abc", @"jkl", @"ghi" };
  const id kValues3[] = { @"abc", @"def", @"ghi", @"jkl" };
  GPBUInt32ObjectDictionary *dict1 =
      [[GPBUInt32ObjectDictionary alloc] initWithValues:kValues1
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1);
  GPBUInt32ObjectDictionary *dict1prime =
      [[GPBUInt32ObjectDictionary alloc] initWithValues:kValues1
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict1prime);
  GPBUInt32ObjectDictionary *dict2 =
      [[GPBUInt32ObjectDictionary alloc] initWithValues:kValues2
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  GPBUInt32ObjectDictionary *dict3 =
      [[GPBUInt32ObjectDictionary alloc] initWithValues:kValues1
                                                forKeys:kKeys2
                                                  count:GPBARRAYSIZE(kValues1)];
  XCTAssertNotNil(dict3);
  GPBUInt32ObjectDictionary *dict4 =
      [[GPBUInt32ObjectDictionary alloc] initWithValues:kValues3
                                                forKeys:kKeys1
                                                  count:GPBARRAYSIZE(kValues3)];
  XCTAssertNotNil(dict4);

  // 1/1Prime should be different objects, but equal.
  XCTAssertNotEqual(dict1, dict1prime);
  XCTAssertEqualObjects(dict1, dict1prime);
  // Equal, so they must have same hash.
  XCTAssertEqual([dict1 hash], [dict1prime hash]);

  // 2 is save keys, different values; not equal.
  XCTAssertNotEqualObjects(dict1, dict2);

  // 3 is different keys, samae values; not equal.
  XCTAssertNotEqualObjects(dict1, dict3);

  // 4 extra pair; not equal
  XCTAssertNotEqualObjects(dict1, dict4);

  [dict1 release];
  [dict1prime release];
  [dict2 release];
  [dict3 release];
  [dict4 release];
}

- (void)testCopy {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const id kValues[] = { @"abc", @"def", @"ghi", @"jkl" };
  GPBUInt32ObjectDictionary *dict =
      [[GPBUInt32ObjectDictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32ObjectDictionary *dict2 = [dict copy];
  XCTAssertNotNil(dict2);

  // Should be new object but equal.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  XCTAssertTrue([dict2 isKindOfClass:[GPBUInt32ObjectDictionary class]]);

  [dict2 release];
  [dict release];
}

- (void)testDictionaryFromDictionary {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const id kValues[] = { @"abc", @"def", @"ghi", @"jkl" };
  GPBUInt32ObjectDictionary *dict =
      [[GPBUInt32ObjectDictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);

  GPBUInt32ObjectDictionary *dict2 =
      [GPBUInt32ObjectDictionary dictionaryWithDictionary:dict];
  XCTAssertNotNil(dict2);

  // Should be new pointer, but equal objects.
  XCTAssertNotEqual(dict, dict2);
  XCTAssertEqualObjects(dict, dict2);
  [dict release];
}

- (void)testAdds {
  GPBUInt32ObjectDictionary *dict = [GPBUInt32ObjectDictionary dictionary];
  XCTAssertNotNil(dict);

  XCTAssertEqual(dict.count, 0U);
  [dict setValue:@"abc" forKey:1U];
  XCTAssertEqual(dict.count, 1U);

  const uint32_t kKeys[] = { 2U, 3U, 4U };
  const id kValues[] = { @"def", @"ghi", @"jkl" };
  GPBUInt32ObjectDictionary *dict2 =
      [[GPBUInt32ObjectDictionary alloc] initWithValues:kValues
                                                forKeys:kKeys
                                                  count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);

  XCTAssertEqualObjects([dict valueForKey:1U], @"abc");
  XCTAssertEqualObjects([dict valueForKey:2U], @"def");
  XCTAssertEqualObjects([dict valueForKey:3U], @"ghi");
  XCTAssertEqualObjects([dict valueForKey:4U], @"jkl");
  [dict2 release];
}

- (void)testRemove {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const id kValues[] = { @"abc", @"def", @"ghi", @"jkl" };
  GPBUInt32ObjectDictionary *dict =
      [[GPBUInt32ObjectDictionary alloc] initWithValues:kValues
                                         forKeys:kKeys
                                           count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);

  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  XCTAssertEqualObjects([dict valueForKey:1U], @"abc");
  XCTAssertNil([dict valueForKey:2U]);
  XCTAssertEqualObjects([dict valueForKey:3U], @"ghi");
  XCTAssertEqualObjects([dict valueForKey:4U], @"jkl");

  // Remove again does nothing.
  [dict removeValueForKey:2U];
  XCTAssertEqual(dict.count, 3U);
  XCTAssertEqualObjects([dict valueForKey:1U], @"abc");
  XCTAssertNil([dict valueForKey:2U]);
  XCTAssertEqualObjects([dict valueForKey:3U], @"ghi");
  XCTAssertEqualObjects([dict valueForKey:4U], @"jkl");

  [dict removeValueForKey:4U];
  XCTAssertEqual(dict.count, 2U);
  XCTAssertEqualObjects([dict valueForKey:1U], @"abc");
  XCTAssertNil([dict valueForKey:2U]);
  XCTAssertEqualObjects([dict valueForKey:3U], @"ghi");
  XCTAssertNil([dict valueForKey:4U]);

  [dict removeAll];
  XCTAssertEqual(dict.count, 0U);
  XCTAssertNil([dict valueForKey:1U]);
  XCTAssertNil([dict valueForKey:2U]);
  XCTAssertNil([dict valueForKey:3U]);
  XCTAssertNil([dict valueForKey:4U]);
  [dict release];
}

- (void)testInplaceMutation {
  const uint32_t kKeys[] = { 1U, 2U, 3U, 4U };
  const id kValues[] = { @"abc", @"def", @"ghi", @"jkl" };
  GPBUInt32ObjectDictionary *dict =
      [[GPBUInt32ObjectDictionary alloc] initWithValues:kValues
                                         forKeys:kKeys
                                           count:GPBARRAYSIZE(kValues)];
  XCTAssertNotNil(dict);
  XCTAssertEqual(dict.count, 4U);
  XCTAssertEqualObjects([dict valueForKey:1U], @"abc");
  XCTAssertEqualObjects([dict valueForKey:2U], @"def");
  XCTAssertEqualObjects([dict valueForKey:3U], @"ghi");
  XCTAssertEqualObjects([dict valueForKey:4U], @"jkl");

  [dict setValue:@"jkl" forKey:1U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertEqualObjects([dict valueForKey:1U], @"jkl");
  XCTAssertEqualObjects([dict valueForKey:2U], @"def");
  XCTAssertEqualObjects([dict valueForKey:3U], @"ghi");
  XCTAssertEqualObjects([dict valueForKey:4U], @"jkl");

  [dict setValue:@"def" forKey:4U];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertEqualObjects([dict valueForKey:1U], @"jkl");
  XCTAssertEqualObjects([dict valueForKey:2U], @"def");
  XCTAssertEqualObjects([dict valueForKey:3U], @"ghi");
  XCTAssertEqualObjects([dict valueForKey:4U], @"def");

  const uint32_t kKeys2[] = { 2U, 3U };
  const id kValues2[] = { @"ghi", @"abc" };
  GPBUInt32ObjectDictionary *dict2 =
      [[GPBUInt32ObjectDictionary alloc] initWithValues:kValues2
                                                forKeys:kKeys2
                                                  count:GPBARRAYSIZE(kValues2)];
  XCTAssertNotNil(dict2);
  [dict addEntriesFromDictionary:dict2];
  XCTAssertEqual(dict.count, 4U);
  XCTAssertEqualObjects([dict valueForKey:1U], @"jkl");
  XCTAssertEqualObjects([dict valueForKey:2U], @"ghi");
  XCTAssertEqualObjects([dict valueForKey:3U], @"abc");
  XCTAssertEqualObjects([dict valueForKey:4U], @"def");

  [dict2 release];
  [dict release];
}

@end

//%PDDM-EXPAND-END TEST_FOR_POD_KEY(UInt32, uint32_t, 1U, 2U, 3U, 4U)

