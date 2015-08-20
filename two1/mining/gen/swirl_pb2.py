# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: swirl.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='swirl.proto',
  package='',
  syntax='proto3',
  serialized_pb=_b('\n\x0bswirl.proto\"\xe6\x02\n\x12SwirlClientMessage\x12\x37\n\x0c\x61uth_request\x18\x64 \x01(\x0b\x32\x1f.SwirlClientMessage.AuthRequestH\x00\x12@\n\x0esubmit_request\x18\x65 \x01(\x0b\x32&.SwirlClientMessage.SubmitShareRequestH\x00\x1aY\n\x0b\x41uthRequest\x12\x0f\n\x07version\x18\x01 \x01(\r\x12\x12\n\nhw_version\x18\x02 \x01(\r\x12\x10\n\x08username\x18\x03 \x01(\t\x12\x13\n\x0bworker_uuid\x18\x04 \x01(\r\x1ah\n\x12SubmitShareRequest\x12\x12\n\nmessage_id\x18\x01 \x01(\r\x12\x0f\n\x07work_id\x18\x02 \x01(\r\x12\x0f\n\x07\x65nonce2\x18\x03 \x01(\x0c\x12\r\n\x05otime\x18\x04 \x01(\r\x12\r\n\x05nonce\x18\x05 \x01(\rB\x10\n\x0e\x63lientmessages\"\x8a\x08\n\x12SwirlServerMessage\x12\x34\n\nauth_reply\x18\xc8\x01 \x01(\x0b\x32\x1d.SwirlServerMessage.AuthReplyH\x00\x12=\n\x0csubmit_reply\x18\xc9\x01 \x01(\x0b\x32$.SwirlServerMessage.SubmitShareReplyH\x00\x12\x42\n\x11work_notification\x18\xca\x01 \x01(\x0b\x32$.SwirlServerMessage.WorkNotificationH\x00\x1a\x86\x03\n\tAuthReply\x12\x44\n\x0e\x61uth_reply_yes\x18\x01 \x01(\x0b\x32*.SwirlServerMessage.AuthReply.AuthReplyYesH\x00\x12\x42\n\rauth_reply_no\x18\x02 \x01(\x0b\x32).SwirlServerMessage.AuthReply.AuthReplyNoH\x00\x12O\n\x14\x61uth_reply_pool_down\x18\x03 \x01(\x0b\x32/.SwirlServerMessage.AuthReply.AuthReplyPoolDownH\x00\x1a\x35\n\x0c\x41uthReplyYes\x12\x0f\n\x07\x65nonce1\x18\x01 \x01(\x0c\x12\x14\n\x0c\x65nonce2_size\x18\x02 \x01(\r\x1a\x1c\n\x0b\x41uthReplyNo\x12\r\n\x05\x65rror\x18\x01 \x01(\t\x1a:\n\x11\x41uthReplyPoolDown\x12\x0e\n\x06reason\x18\x01 \x01(\t\x12\x15\n\rretry_seconds\x18\x02 \x01(\rB\r\n\x0b\x61uthreplies\x1a\xad\x01\n\x10SubmitShareReply\x12\x12\n\nmessage_id\x18\x01 \x01(\r\x12H\n\rsubmit_status\x18\x02 \x01(\x0e\x32\x31.SwirlServerMessage.SubmitShareReply.SubmitStatus\";\n\x0cSubmitStatus\x12\x07\n\x03\x62\x61\x64\x10\x00\x12\x08\n\x04good\x10\x01\x12\t\n\x05stale\x10\x02\x12\r\n\tduplicate\x10\x03\x1a\xef\x01\n\x10WorkNotification\x12\x0f\n\x07work_id\x18\x01 \x01(\r\x12\x15\n\rblock_version\x18\x02 \x01(\r\x12\x17\n\x0fprev_block_hash\x18\x03 \x01(\x0c\x12\x14\n\x0c\x62lock_height\x18\x04 \x01(\r\x12\x0c\n\x04\x62its\x18\x05 \x01(\r\x12\r\n\x05itime\x18\x06 \x01(\r\x12\x10\n\x08iscript0\x18\x07 \x01(\x0c\x12\x10\n\x08iscript1\x18\x08 \x01(\x0c\x12\x0f\n\x07outputs\x18\t \x03(\x0c\x12\x0c\n\x04\x65\x64ge\x18\n \x03(\x0c\x12\x11\n\tnew_block\x18\x0b \x01(\x08\x12\x11\n\tbits_pool\x18\x0c \x01(\rB\x10\n\x0eservermessagesb\x06proto3')
)
_sym_db.RegisterFileDescriptor(DESCRIPTOR)



_SWIRLSERVERMESSAGE_SUBMITSHAREREPLY_SUBMITSTATUS = _descriptor.EnumDescriptor(
  name='SubmitStatus',
  full_name='SwirlServerMessage.SubmitShareReply.SubmitStatus',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='bad', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='good', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='stale', index=2, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='duplicate', index=3, number=3,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=1092,
  serialized_end=1151,
)
_sym_db.RegisterEnumDescriptor(_SWIRLSERVERMESSAGE_SUBMITSHAREREPLY_SUBMITSTATUS)


_SWIRLCLIENTMESSAGE_AUTHREQUEST = _descriptor.Descriptor(
  name='AuthRequest',
  full_name='SwirlClientMessage.AuthRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='version', full_name='SwirlClientMessage.AuthRequest.version', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='hw_version', full_name='SwirlClientMessage.AuthRequest.hw_version', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='username', full_name='SwirlClientMessage.AuthRequest.username', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='worker_uuid', full_name='SwirlClientMessage.AuthRequest.worker_uuid', index=3,
      number=4, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=161,
  serialized_end=250,
)

_SWIRLCLIENTMESSAGE_SUBMITSHAREREQUEST = _descriptor.Descriptor(
  name='SubmitShareRequest',
  full_name='SwirlClientMessage.SubmitShareRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='message_id', full_name='SwirlClientMessage.SubmitShareRequest.message_id', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='work_id', full_name='SwirlClientMessage.SubmitShareRequest.work_id', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='enonce2', full_name='SwirlClientMessage.SubmitShareRequest.enonce2', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='otime', full_name='SwirlClientMessage.SubmitShareRequest.otime', index=3,
      number=4, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='nonce', full_name='SwirlClientMessage.SubmitShareRequest.nonce', index=4,
      number=5, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=252,
  serialized_end=356,
)

_SWIRLCLIENTMESSAGE = _descriptor.Descriptor(
  name='SwirlClientMessage',
  full_name='SwirlClientMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='auth_request', full_name='SwirlClientMessage.auth_request', index=0,
      number=100, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='submit_request', full_name='SwirlClientMessage.submit_request', index=1,
      number=101, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_SWIRLCLIENTMESSAGE_AUTHREQUEST, _SWIRLCLIENTMESSAGE_SUBMITSHAREREQUEST, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
    _descriptor.OneofDescriptor(
      name='clientmessages', full_name='SwirlClientMessage.clientmessages',
      index=0, containing_type=None, fields=[]),
  ],
  serialized_start=16,
  serialized_end=374,
)


_SWIRLSERVERMESSAGE_AUTHREPLY_AUTHREPLYYES = _descriptor.Descriptor(
  name='AuthReplyYes',
  full_name='SwirlServerMessage.AuthReply.AuthReplyYes',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='enonce1', full_name='SwirlServerMessage.AuthReply.AuthReplyYes.enonce1', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='enonce2_size', full_name='SwirlServerMessage.AuthReply.AuthReplyYes.enonce2_size', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=817,
  serialized_end=870,
)

_SWIRLSERVERMESSAGE_AUTHREPLY_AUTHREPLYNO = _descriptor.Descriptor(
  name='AuthReplyNo',
  full_name='SwirlServerMessage.AuthReply.AuthReplyNo',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='error', full_name='SwirlServerMessage.AuthReply.AuthReplyNo.error', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=872,
  serialized_end=900,
)

_SWIRLSERVERMESSAGE_AUTHREPLY_AUTHREPLYPOOLDOWN = _descriptor.Descriptor(
  name='AuthReplyPoolDown',
  full_name='SwirlServerMessage.AuthReply.AuthReplyPoolDown',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='reason', full_name='SwirlServerMessage.AuthReply.AuthReplyPoolDown.reason', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='retry_seconds', full_name='SwirlServerMessage.AuthReply.AuthReplyPoolDown.retry_seconds', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=902,
  serialized_end=960,
)

_SWIRLSERVERMESSAGE_AUTHREPLY = _descriptor.Descriptor(
  name='AuthReply',
  full_name='SwirlServerMessage.AuthReply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='auth_reply_yes', full_name='SwirlServerMessage.AuthReply.auth_reply_yes', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='auth_reply_no', full_name='SwirlServerMessage.AuthReply.auth_reply_no', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='auth_reply_pool_down', full_name='SwirlServerMessage.AuthReply.auth_reply_pool_down', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_SWIRLSERVERMESSAGE_AUTHREPLY_AUTHREPLYYES, _SWIRLSERVERMESSAGE_AUTHREPLY_AUTHREPLYNO, _SWIRLSERVERMESSAGE_AUTHREPLY_AUTHREPLYPOOLDOWN, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
    _descriptor.OneofDescriptor(
      name='authreplies', full_name='SwirlServerMessage.AuthReply.authreplies',
      index=0, containing_type=None, fields=[]),
  ],
  serialized_start=585,
  serialized_end=975,
)

_SWIRLSERVERMESSAGE_SUBMITSHAREREPLY = _descriptor.Descriptor(
  name='SubmitShareReply',
  full_name='SwirlServerMessage.SubmitShareReply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='message_id', full_name='SwirlServerMessage.SubmitShareReply.message_id', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='submit_status', full_name='SwirlServerMessage.SubmitShareReply.submit_status', index=1,
      number=2, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _SWIRLSERVERMESSAGE_SUBMITSHAREREPLY_SUBMITSTATUS,
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=978,
  serialized_end=1151,
)

_SWIRLSERVERMESSAGE_WORKNOTIFICATION = _descriptor.Descriptor(
  name='WorkNotification',
  full_name='SwirlServerMessage.WorkNotification',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='work_id', full_name='SwirlServerMessage.WorkNotification.work_id', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='block_version', full_name='SwirlServerMessage.WorkNotification.block_version', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='prev_block_hash', full_name='SwirlServerMessage.WorkNotification.prev_block_hash', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='block_height', full_name='SwirlServerMessage.WorkNotification.block_height', index=3,
      number=4, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='bits', full_name='SwirlServerMessage.WorkNotification.bits', index=4,
      number=5, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='itime', full_name='SwirlServerMessage.WorkNotification.itime', index=5,
      number=6, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='iscript0', full_name='SwirlServerMessage.WorkNotification.iscript0', index=6,
      number=7, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='iscript1', full_name='SwirlServerMessage.WorkNotification.iscript1', index=7,
      number=8, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='outputs', full_name='SwirlServerMessage.WorkNotification.outputs', index=8,
      number=9, type=12, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='edge', full_name='SwirlServerMessage.WorkNotification.edge', index=9,
      number=10, type=12, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='new_block', full_name='SwirlServerMessage.WorkNotification.new_block', index=10,
      number=11, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='bits_pool', full_name='SwirlServerMessage.WorkNotification.bits_pool', index=11,
      number=12, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1154,
  serialized_end=1393,
)

_SWIRLSERVERMESSAGE = _descriptor.Descriptor(
  name='SwirlServerMessage',
  full_name='SwirlServerMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='auth_reply', full_name='SwirlServerMessage.auth_reply', index=0,
      number=200, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='submit_reply', full_name='SwirlServerMessage.submit_reply', index=1,
      number=201, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='work_notification', full_name='SwirlServerMessage.work_notification', index=2,
      number=202, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_SWIRLSERVERMESSAGE_AUTHREPLY, _SWIRLSERVERMESSAGE_SUBMITSHAREREPLY, _SWIRLSERVERMESSAGE_WORKNOTIFICATION, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
    _descriptor.OneofDescriptor(
      name='servermessages', full_name='SwirlServerMessage.servermessages',
      index=0, containing_type=None, fields=[]),
  ],
  serialized_start=377,
  serialized_end=1411,
)

_SWIRLCLIENTMESSAGE_AUTHREQUEST.containing_type = _SWIRLCLIENTMESSAGE
_SWIRLCLIENTMESSAGE_SUBMITSHAREREQUEST.containing_type = _SWIRLCLIENTMESSAGE
_SWIRLCLIENTMESSAGE.fields_by_name['auth_request'].message_type = _SWIRLCLIENTMESSAGE_AUTHREQUEST
_SWIRLCLIENTMESSAGE.fields_by_name['submit_request'].message_type = _SWIRLCLIENTMESSAGE_SUBMITSHAREREQUEST
_SWIRLCLIENTMESSAGE.oneofs_by_name['clientmessages'].fields.append(
  _SWIRLCLIENTMESSAGE.fields_by_name['auth_request'])
_SWIRLCLIENTMESSAGE.fields_by_name['auth_request'].containing_oneof = _SWIRLCLIENTMESSAGE.oneofs_by_name['clientmessages']
_SWIRLCLIENTMESSAGE.oneofs_by_name['clientmessages'].fields.append(
  _SWIRLCLIENTMESSAGE.fields_by_name['submit_request'])
_SWIRLCLIENTMESSAGE.fields_by_name['submit_request'].containing_oneof = _SWIRLCLIENTMESSAGE.oneofs_by_name['clientmessages']
_SWIRLSERVERMESSAGE_AUTHREPLY_AUTHREPLYYES.containing_type = _SWIRLSERVERMESSAGE_AUTHREPLY
_SWIRLSERVERMESSAGE_AUTHREPLY_AUTHREPLYNO.containing_type = _SWIRLSERVERMESSAGE_AUTHREPLY
_SWIRLSERVERMESSAGE_AUTHREPLY_AUTHREPLYPOOLDOWN.containing_type = _SWIRLSERVERMESSAGE_AUTHREPLY
_SWIRLSERVERMESSAGE_AUTHREPLY.fields_by_name['auth_reply_yes'].message_type = _SWIRLSERVERMESSAGE_AUTHREPLY_AUTHREPLYYES
_SWIRLSERVERMESSAGE_AUTHREPLY.fields_by_name['auth_reply_no'].message_type = _SWIRLSERVERMESSAGE_AUTHREPLY_AUTHREPLYNO
_SWIRLSERVERMESSAGE_AUTHREPLY.fields_by_name['auth_reply_pool_down'].message_type = _SWIRLSERVERMESSAGE_AUTHREPLY_AUTHREPLYPOOLDOWN
_SWIRLSERVERMESSAGE_AUTHREPLY.containing_type = _SWIRLSERVERMESSAGE
_SWIRLSERVERMESSAGE_AUTHREPLY.oneofs_by_name['authreplies'].fields.append(
  _SWIRLSERVERMESSAGE_AUTHREPLY.fields_by_name['auth_reply_yes'])
_SWIRLSERVERMESSAGE_AUTHREPLY.fields_by_name['auth_reply_yes'].containing_oneof = _SWIRLSERVERMESSAGE_AUTHREPLY.oneofs_by_name['authreplies']
_SWIRLSERVERMESSAGE_AUTHREPLY.oneofs_by_name['authreplies'].fields.append(
  _SWIRLSERVERMESSAGE_AUTHREPLY.fields_by_name['auth_reply_no'])
_SWIRLSERVERMESSAGE_AUTHREPLY.fields_by_name['auth_reply_no'].containing_oneof = _SWIRLSERVERMESSAGE_AUTHREPLY.oneofs_by_name['authreplies']
_SWIRLSERVERMESSAGE_AUTHREPLY.oneofs_by_name['authreplies'].fields.append(
  _SWIRLSERVERMESSAGE_AUTHREPLY.fields_by_name['auth_reply_pool_down'])
_SWIRLSERVERMESSAGE_AUTHREPLY.fields_by_name['auth_reply_pool_down'].containing_oneof = _SWIRLSERVERMESSAGE_AUTHREPLY.oneofs_by_name['authreplies']
_SWIRLSERVERMESSAGE_SUBMITSHAREREPLY.fields_by_name['submit_status'].enum_type = _SWIRLSERVERMESSAGE_SUBMITSHAREREPLY_SUBMITSTATUS
_SWIRLSERVERMESSAGE_SUBMITSHAREREPLY.containing_type = _SWIRLSERVERMESSAGE
_SWIRLSERVERMESSAGE_SUBMITSHAREREPLY_SUBMITSTATUS.containing_type = _SWIRLSERVERMESSAGE_SUBMITSHAREREPLY
_SWIRLSERVERMESSAGE_WORKNOTIFICATION.containing_type = _SWIRLSERVERMESSAGE
_SWIRLSERVERMESSAGE.fields_by_name['auth_reply'].message_type = _SWIRLSERVERMESSAGE_AUTHREPLY
_SWIRLSERVERMESSAGE.fields_by_name['submit_reply'].message_type = _SWIRLSERVERMESSAGE_SUBMITSHAREREPLY
_SWIRLSERVERMESSAGE.fields_by_name['work_notification'].message_type = _SWIRLSERVERMESSAGE_WORKNOTIFICATION
_SWIRLSERVERMESSAGE.oneofs_by_name['servermessages'].fields.append(
  _SWIRLSERVERMESSAGE.fields_by_name['auth_reply'])
_SWIRLSERVERMESSAGE.fields_by_name['auth_reply'].containing_oneof = _SWIRLSERVERMESSAGE.oneofs_by_name['servermessages']
_SWIRLSERVERMESSAGE.oneofs_by_name['servermessages'].fields.append(
  _SWIRLSERVERMESSAGE.fields_by_name['submit_reply'])
_SWIRLSERVERMESSAGE.fields_by_name['submit_reply'].containing_oneof = _SWIRLSERVERMESSAGE.oneofs_by_name['servermessages']
_SWIRLSERVERMESSAGE.oneofs_by_name['servermessages'].fields.append(
  _SWIRLSERVERMESSAGE.fields_by_name['work_notification'])
_SWIRLSERVERMESSAGE.fields_by_name['work_notification'].containing_oneof = _SWIRLSERVERMESSAGE.oneofs_by_name['servermessages']
DESCRIPTOR.message_types_by_name['SwirlClientMessage'] = _SWIRLCLIENTMESSAGE
DESCRIPTOR.message_types_by_name['SwirlServerMessage'] = _SWIRLSERVERMESSAGE

SwirlClientMessage = _reflection.GeneratedProtocolMessageType('SwirlClientMessage', (_message.Message,), dict(

  AuthRequest = _reflection.GeneratedProtocolMessageType('AuthRequest', (_message.Message,), dict(
    DESCRIPTOR = _SWIRLCLIENTMESSAGE_AUTHREQUEST,
    __module__ = 'swirl_pb2'
    # @@protoc_insertion_point(class_scope:SwirlClientMessage.AuthRequest)
    ))
  ,

  SubmitShareRequest = _reflection.GeneratedProtocolMessageType('SubmitShareRequest', (_message.Message,), dict(
    DESCRIPTOR = _SWIRLCLIENTMESSAGE_SUBMITSHAREREQUEST,
    __module__ = 'swirl_pb2'
    # @@protoc_insertion_point(class_scope:SwirlClientMessage.SubmitShareRequest)
    ))
  ,
  DESCRIPTOR = _SWIRLCLIENTMESSAGE,
  __module__ = 'swirl_pb2'
  # @@protoc_insertion_point(class_scope:SwirlClientMessage)
  ))
_sym_db.RegisterMessage(SwirlClientMessage)
_sym_db.RegisterMessage(SwirlClientMessage.AuthRequest)
_sym_db.RegisterMessage(SwirlClientMessage.SubmitShareRequest)

SwirlServerMessage = _reflection.GeneratedProtocolMessageType('SwirlServerMessage', (_message.Message,), dict(

  AuthReply = _reflection.GeneratedProtocolMessageType('AuthReply', (_message.Message,), dict(

    AuthReplyYes = _reflection.GeneratedProtocolMessageType('AuthReplyYes', (_message.Message,), dict(
      DESCRIPTOR = _SWIRLSERVERMESSAGE_AUTHREPLY_AUTHREPLYYES,
      __module__ = 'swirl_pb2'
      # @@protoc_insertion_point(class_scope:SwirlServerMessage.AuthReply.AuthReplyYes)
      ))
    ,

    AuthReplyNo = _reflection.GeneratedProtocolMessageType('AuthReplyNo', (_message.Message,), dict(
      DESCRIPTOR = _SWIRLSERVERMESSAGE_AUTHREPLY_AUTHREPLYNO,
      __module__ = 'swirl_pb2'
      # @@protoc_insertion_point(class_scope:SwirlServerMessage.AuthReply.AuthReplyNo)
      ))
    ,

    AuthReplyPoolDown = _reflection.GeneratedProtocolMessageType('AuthReplyPoolDown', (_message.Message,), dict(
      DESCRIPTOR = _SWIRLSERVERMESSAGE_AUTHREPLY_AUTHREPLYPOOLDOWN,
      __module__ = 'swirl_pb2'
      # @@protoc_insertion_point(class_scope:SwirlServerMessage.AuthReply.AuthReplyPoolDown)
      ))
    ,
    DESCRIPTOR = _SWIRLSERVERMESSAGE_AUTHREPLY,
    __module__ = 'swirl_pb2'
    # @@protoc_insertion_point(class_scope:SwirlServerMessage.AuthReply)
    ))
  ,

  SubmitShareReply = _reflection.GeneratedProtocolMessageType('SubmitShareReply', (_message.Message,), dict(
    DESCRIPTOR = _SWIRLSERVERMESSAGE_SUBMITSHAREREPLY,
    __module__ = 'swirl_pb2'
    # @@protoc_insertion_point(class_scope:SwirlServerMessage.SubmitShareReply)
    ))
  ,

  WorkNotification = _reflection.GeneratedProtocolMessageType('WorkNotification', (_message.Message,), dict(
    DESCRIPTOR = _SWIRLSERVERMESSAGE_WORKNOTIFICATION,
    __module__ = 'swirl_pb2'
    # @@protoc_insertion_point(class_scope:SwirlServerMessage.WorkNotification)
    ))
  ,
  DESCRIPTOR = _SWIRLSERVERMESSAGE,
  __module__ = 'swirl_pb2'
  # @@protoc_insertion_point(class_scope:SwirlServerMessage)
  ))
_sym_db.RegisterMessage(SwirlServerMessage)
_sym_db.RegisterMessage(SwirlServerMessage.AuthReply)
_sym_db.RegisterMessage(SwirlServerMessage.AuthReply.AuthReplyYes)
_sym_db.RegisterMessage(SwirlServerMessage.AuthReply.AuthReplyNo)
_sym_db.RegisterMessage(SwirlServerMessage.AuthReply.AuthReplyPoolDown)
_sym_db.RegisterMessage(SwirlServerMessage.SubmitShareReply)
_sym_db.RegisterMessage(SwirlServerMessage.WorkNotification)


# @@protoc_insertion_point(module_scope)
