// Protocol Buffers - Google's data interchange format
// Copyright 2014 Google Inc.  All rights reserved.
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

#include "protobuf.h"

// -----------------------------------------------------------------------------
// Parsing.
// -----------------------------------------------------------------------------

#define DEREF(msg, ofs, type) *(type*)(((uint8_t *)msg) + ofs)

// Creates a handlerdata that simply contains the offset for this field.
static const void* newhandlerdata(upb_handlers* h, uint32_t ofs) {
  size_t* hd_ofs = ALLOC(size_t);
  *hd_ofs = ofs;
  upb_handlers_addcleanup(h, hd_ofs, free);
  return hd_ofs;
}

typedef struct {
  size_t ofs;
  const upb_msgdef *md;
} submsg_handlerdata_t;

// Creates a handlerdata that contains offset and submessage type information.
static const void *newsubmsghandlerdata(upb_handlers* h, uint32_t ofs,
                                        const upb_fielddef* f) {
  submsg_handlerdata_t *hd = ALLOC(submsg_handlerdata_t);
  hd->ofs = ofs;
  hd->md = upb_fielddef_msgsubdef(f);
  upb_handlers_addcleanup(h, hd, free);
  return hd;
}

typedef struct {
  size_t ofs;              // union data slot
  size_t case_ofs;         // oneof_case field
  uint32_t oneof_case_num; // oneof-case number to place in oneof_case field
  const upb_msgdef *md;    // msgdef, for oneof submessage handler
} oneof_handlerdata_t;

static const void *newoneofhandlerdata(upb_handlers *h,
                                       uint32_t ofs,
                                       uint32_t case_ofs,
                                       const upb_fielddef *f) {
  oneof_handlerdata_t *hd = ALLOC(oneof_handlerdata_t);
  hd->ofs = ofs;
  hd->case_ofs = case_ofs;
  // We reuse the field tag number as a oneof union discriminant tag. Note that
  // we don't expose these numbers to the user, so the only requirement is that
  // we have some unique ID for each union case/possibility. The field tag
  // numbers are already present and are easy to use so there's no reason to
  // create a separate ID space. In addition, using the field tag number here
  // lets us easily look up the field in the oneof accessor.
  hd->oneof_case_num = upb_fielddef_number(f);
  if (upb_fielddef_type(f) == UPB_TYPE_MESSAGE) {
    hd->md = upb_fielddef_msgsubdef(f);
  } else {
    hd->md = NULL;
  }
  upb_handlers_addcleanup(h, hd, free);
  return hd;
}

// A handler that starts a repeated field.  Gets the Repeated*Field instance for
// this field (such an instance always exists even in an empty message).
static void *startseq_handler(void* closure, const void* hd) {
  MessageHeader* msg = closure;
  const size_t *ofs = hd;
  return (void*)DEREF(msg, *ofs, VALUE);
}

// Handlers that append primitive values to a repeated field.
#define DEFINE_APPEND_HANDLER(type, ctype)                 \
  static bool append##type##_handler(void *closure, const void *hd, \
                                     ctype val) {                   \
    VALUE ary = (VALUE)closure;                                     \
    RepeatedField_push_native(ary, &val);                           \
    return true;                                                    \
  }

DEFINE_APPEND_HANDLER(bool,   bool)
DEFINE_APPEND_HANDLER(int32,  int32_t)
DEFINE_APPEND_HANDLER(uint32, uint32_t)
DEFINE_APPEND_HANDLER(float,  float)
DEFINE_APPEND_HANDLER(int64,  int64_t)
DEFINE_APPEND_HANDLER(uint64, uint64_t)
DEFINE_APPEND_HANDLER(double, double)

// Appends a string to a repeated field.
static void* appendstr_handler(void *closure,
                               const void *hd,
                               size_t size_hint) {
  VALUE ary = (VALUE)closure;
  VALUE str = rb_str_new2("");
  rb_enc_associate(str, kRubyStringUtf8Encoding);
  RepeatedField_push(ary, str);
  return (void*)str;
}

// Appends a 'bytes' string to a repeated field.
static void* appendbytes_handler(void *closure,
                                 const void *hd,
                                 size_t size_hint) {
  VALUE ary = (VALUE)closure;
  VALUE str = rb_str_new2("");
  rb_enc_associate(str, kRubyString8bitEncoding);
  RepeatedField_push(ary, str);
  return (void*)str;
}

// Sets a non-repeated string field in a message.
static void* str_handler(void *closure,
                         const void *hd,
                         size_t size_hint) {
  MessageHeader* msg = closure;
  const size_t *ofs = hd;
  VALUE str = rb_str_new2("");
  rb_enc_associate(str, kRubyStringUtf8Encoding);
  DEREF(msg, *ofs, VALUE) = str;
  return (void*)str;
}

// Sets a non-repeated 'bytes' field in a message.
static void* bytes_handler(void *closure,
                           const void *hd,
                           size_t size_hint) {
  MessageHeader* msg = closure;
  const size_t *ofs = hd;
  VALUE str = rb_str_new2("");
  rb_enc_associate(str, kRubyString8bitEncoding);
  DEREF(msg, *ofs, VALUE) = str;
  return (void*)str;
}

static size_t stringdata_handler(void* closure, const void* hd,
                                 const char* str, size_t len,
                                 const upb_bufhandle* handle) {
  VALUE rb_str = (VALUE)closure;
  rb_str_cat(rb_str, str, len);
  return len;
}

// Appends a submessage to a repeated field (a regular Ruby array for now).
static void *appendsubmsg_handler(void *closure, const void *hd) {
  VALUE ary = (VALUE)closure;
  const submsg_handlerdata_t *submsgdata = hd;
  VALUE subdesc =
      get_def_obj((void*)submsgdata->md);
  VALUE subklass = Descriptor_msgclass(subdesc);

  VALUE submsg_rb = rb_class_new_instance(0, NULL, subklass);
  RepeatedField_push(ary, submsg_rb);

  MessageHeader* submsg;
  TypedData_Get_Struct(submsg_rb, MessageHeader, &Message_type, submsg);
  return submsg;
}

// Sets a non-repeated submessage field in a message.
static void *submsg_handler(void *closure, const void *hd) {
  MessageHeader* msg = closure;
  const submsg_handlerdata_t* submsgdata = hd;
  VALUE subdesc =
      get_def_obj((void*)submsgdata->md);
  VALUE subklass = Descriptor_msgclass(subdesc);

  if (DEREF(msg, submsgdata->ofs, VALUE) == Qnil) {
    DEREF(msg, submsgdata->ofs, VALUE) =
        rb_class_new_instance(0, NULL, subklass);
  }

  VALUE submsg_rb = DEREF(msg, submsgdata->ofs, VALUE);
  MessageHeader* submsg;
  TypedData_Get_Struct(submsg_rb, MessageHeader, &Message_type, submsg);
  return submsg;
}

// Handler data for startmap/endmap handlers.
typedef struct {
  size_t ofs;
  upb_fieldtype_t key_field_type;
  upb_fieldtype_t value_field_type;

  // We know that we can hold this reference because the handlerdata has the
  // same lifetime as the upb_handlers struct, and the upb_handlers struct holds
  // a reference to the upb_msgdef, which in turn has references to its subdefs.
  const upb_def* value_field_subdef;
} map_handlerdata_t;

// Temporary frame for map parsing: at the beginning of a map entry message, a
// submsg handler allocates a frame to hold (i) a reference to the Map object
// into which this message will be inserted and (ii) storage slots to
// temporarily hold the key and value for this map entry until the end of the
// submessage. When the submessage ends, another handler is called to insert the
// value into the map.
typedef struct {
  VALUE map;
  char key_storage[NATIVE_SLOT_MAX_SIZE];
  char value_storage[NATIVE_SLOT_MAX_SIZE];
} map_parse_frame_t;

// Handler to begin a map entry: allocates a temporary frame. This is the
// 'startsubmsg' handler on the msgdef that contains the map field.
static void *startmapentry_handler(void *closure, const void *hd) {
  MessageHeader* msg = closure;
  const map_handlerdata_t* mapdata = hd;
  VALUE map_rb = DEREF(msg, mapdata->ofs, VALUE);

  map_parse_frame_t* frame = ALLOC(map_parse_frame_t);
  frame->map = map_rb;

  native_slot_init(mapdata->key_field_type, &frame->key_storage);
  native_slot_init(mapdata->value_field_type, &frame->value_storage);

  return frame;
}

// Handler to end a map entry: inserts the value defined during the message into
// the map. This is the 'endmsg' handler on the map entry msgdef.
static bool endmap_handler(void *closure, const void *hd, upb_status* s) {
  map_parse_frame_t* frame = closure;
  const map_handlerdata_t* mapdata = hd;

  VALUE key = native_slot_get(
      mapdata->key_field_type, Qnil,
      &frame->key_storage);

  VALUE value_field_typeclass = Qnil;
  if (mapdata->value_field_type == UPB_TYPE_MESSAGE ||
      mapdata->value_field_type == UPB_TYPE_ENUM) {
    value_field_typeclass = get_def_obj(mapdata->value_field_subdef);
  }

  VALUE value = native_slot_get(
      mapdata->value_field_type, value_field_typeclass,
      &frame->value_storage);

  Map_index_set(frame->map, key, value);
  free(frame);

  return true;
}

// Allocates a new map_handlerdata_t given the map entry message definition. If
// the offset of the field within the parent message is also given, that is
// added to the handler data as well. Note that this is called *twice* per map
// field: once in the parent message handler setup when setting the startsubmsg
// handler and once in the map entry message handler setup when setting the
// key/value and endmsg handlers. The reason is that there is no easy way to
// pass the handlerdata down to the sub-message handler setup.
static map_handlerdata_t* new_map_handlerdata(
    size_t ofs,
    const upb_msgdef* mapentry_def,
    Descriptor* desc) {

  map_handlerdata_t* hd = ALLOC(map_handlerdata_t);
  hd->ofs = ofs;
  const upb_fielddef* key_field = upb_msgdef_itof(mapentry_def,
                                                  MAP_KEY_FIELD);
  assert(key_field != NULL);
  hd->key_field_type = upb_fielddef_type(key_field);
  const upb_fielddef* value_field = upb_msgdef_itof(mapentry_def,
                                                    MAP_VALUE_FIELD);
  assert(value_field != NULL);
  hd->value_field_type = upb_fielddef_type(value_field);
  hd->value_field_subdef = upb_fielddef_subdef(value_field);

  return hd;
}

// Handlers that set primitive values in oneofs.
#define DEFINE_ONEOF_HANDLER(type, ctype)                           \
  static bool oneof##type##_handler(void *closure, const void *hd,  \
                                     ctype val) {                   \
    const oneof_handlerdata_t *oneofdata = hd;                      \
    DEREF(closure, oneofdata->case_ofs, uint32_t) =                 \
        oneofdata->oneof_case_num;                                  \
    DEREF(closure, oneofdata->ofs, ctype) = val;                    \
    return true;                                                    \
  }

DEFINE_ONEOF_HANDLER(bool,   bool)
DEFINE_ONEOF_HANDLER(int32,  int32_t)
DEFINE_ONEOF_HANDLER(uint32, uint32_t)
DEFINE_ONEOF_HANDLER(float,  float)
DEFINE_ONEOF_HANDLER(int64,  int64_t)
DEFINE_ONEOF_HANDLER(uint64, uint64_t)
DEFINE_ONEOF_HANDLER(double, double)

#undef DEFINE_ONEOF_HANDLER

// Handlers for strings in a oneof.
static void *oneofstr_handler(void *closure,
                              const void *hd,
                              size_t size_hint) {
  MessageHeader* msg = closure;
  const oneof_handlerdata_t *oneofdata = hd;
  VALUE str = rb_str_new2("");
  rb_enc_associate(str, kRubyStringUtf8Encoding);
  DEREF(msg, oneofdata->case_ofs, uint32_t) =
      oneofdata->oneof_case_num;
  DEREF(msg, oneofdata->ofs, VALUE) = str;
  return (void*)str;
}

static void *oneofbytes_handler(void *closure,
                                const void *hd,
                                size_t size_hint) {
  MessageHeader* msg = closure;
  const oneof_handlerdata_t *oneofdata = hd;
  VALUE str = rb_str_new2("");
  rb_enc_associate(str, kRubyString8bitEncoding);
  DEREF(msg, oneofdata->case_ofs, uint32_t) =
      oneofdata->oneof_case_num;
  DEREF(msg, oneofdata->ofs, VALUE) = str;
  return (void*)str;
}

// Handler for a submessage field in a oneof.
static void *oneofsubmsg_handler(void *closure,
                                 const void *hd) {
  MessageHeader* msg = closure;
  const oneof_handlerdata_t *oneofdata = hd;
  uint32_t oldcase = DEREF(msg, oneofdata->case_ofs, uint32_t);

  VALUE subdesc =
      get_def_obj((void*)oneofdata->md);
  VALUE subklass = Descriptor_msgclass(subdesc);

  if (oldcase != oneofdata->oneof_case_num ||
      DEREF(msg, oneofdata->ofs, VALUE) == Qnil) {
    DEREF(msg, oneofdata->ofs, VALUE) =
        rb_class_new_instance(0, NULL, subklass);
  }
  // Set the oneof case *after* allocating the new class instance -- otherwise,
  // if the Ruby GC is invoked as part of a call into the VM, it might invoke
  // our mark routines, and our mark routines might see the case value
  // indicating a VALUE is present and expect a valid VALUE. See comment in
  // layout_set() for more detail: basically, the change to the value and the
  // case must be atomic w.r.t. the Ruby VM.
  DEREF(msg, oneofdata->case_ofs, uint32_t) =
      oneofdata->oneof_case_num;

  VALUE submsg_rb = DEREF(msg, oneofdata->ofs, VALUE);
  MessageHeader* submsg;
  TypedData_Get_Struct(submsg_rb, MessageHeader, &Message_type, submsg);
  return submsg;
}

// Set up handlers for a repeated field.
static void add_handlers_for_repeated_field(upb_handlers *h,
                                            const upb_fielddef *f,
                                            size_t offset) {
  upb_handlerattr attr = UPB_HANDLERATTR_INITIALIZER;
  upb_handlerattr_sethandlerdata(&attr, newhandlerdata(h, offset));
  upb_handlers_setstartseq(h, f, startseq_handler, &attr);
  upb_handlerattr_uninit(&attr);

  switch (upb_fielddef_type(f)) {

#define SET_HANDLER(utype, ltype)                                 \
  case utype:                                                     \
    upb_handlers_set##ltype(h, f, append##ltype##_handler, NULL); \
    break;

    SET_HANDLER(UPB_TYPE_BOOL,   bool);
    SET_HANDLER(UPB_TYPE_INT32,  int32);
    SET_HANDLER(UPB_TYPE_UINT32, uint32);
    SET_HANDLER(UPB_TYPE_ENUM,   int32);
    SET_HANDLER(UPB_TYPE_FLOAT,  float);
    SET_HANDLER(UPB_TYPE_INT64,  int64);
    SET_HANDLER(UPB_TYPE_UINT64, uint64);
    SET_HANDLER(UPB_TYPE_DOUBLE, double);

#undef SET_HANDLER

    case UPB_TYPE_STRING:
    case UPB_TYPE_BYTES: {
      bool is_bytes = upb_fielddef_type(f) == UPB_TYPE_BYTES;
      upb_handlers_setstartstr(h, f, is_bytes ?
                               appendbytes_handler : appendstr_handler,
                               NULL);
      upb_handlers_setstring(h, f, stringdata_handler, NULL);
      break;
    }
    case UPB_TYPE_MESSAGE: {
      upb_handlerattr attr = UPB_HANDLERATTR_INITIALIZER;
      upb_handlerattr_sethandlerdata(&attr, newsubmsghandlerdata(h, 0, f));
      upb_handlers_setstartsubmsg(h, f, appendsubmsg_handler, &attr);
      upb_handlerattr_uninit(&attr);
      break;
    }
  }
}

// Set up handlers for a singular field.
static void add_handlers_for_singular_field(upb_handlers *h,
                                            const upb_fielddef *f,
                                            size_t offset) {
  switch (upb_fielddef_type(f)) {
    case UPB_TYPE_BOOL:
    case UPB_TYPE_INT32:
    case UPB_TYPE_UINT32:
    case UPB_TYPE_ENUM:
    case UPB_TYPE_FLOAT:
    case UPB_TYPE_INT64:
    case UPB_TYPE_UINT64:
    case UPB_TYPE_DOUBLE:
      upb_shim_set(h, f, offset, -1);
      break;
    case UPB_TYPE_STRING:
    case UPB_TYPE_BYTES: {
      bool is_bytes = upb_fielddef_type(f) == UPB_TYPE_BYTES;
      upb_handlerattr attr = UPB_HANDLERATTR_INITIALIZER;
      upb_handlerattr_sethandlerdata(&attr, newhandlerdata(h, offset));
      upb_handlers_setstartstr(h, f,
                               is_bytes ? bytes_handler : str_handler,
                               &attr);
      upb_handlers_setstring(h, f, stringdata_handler, &attr);
      upb_handlerattr_uninit(&attr);
      break;
    }
    case UPB_TYPE_MESSAGE: {
      upb_handlerattr attr = UPB_HANDLERATTR_INITIALIZER;
      upb_handlerattr_sethandlerdata(&attr, newsubmsghandlerdata(h, offset, f));
      upb_handlers_setstartsubmsg(h, f, submsg_handler, &attr);
      upb_handlerattr_uninit(&attr);
      break;
    }
  }
}

// Adds handlers to a map field.
static void add_handlers_for_mapfield(upb_handlers* h,
                                      const upb_fielddef* fielddef,
                                      size_t offset,
                                      Descriptor* desc) {
  const upb_msgdef* map_msgdef = upb_fielddef_msgsubdef(fielddef);
  map_handlerdata_t* hd = new_map_handlerdata(offset, map_msgdef, desc);
  upb_handlers_addcleanup(h, hd, free);
  upb_handlerattr attr = UPB_HANDLERATTR_INITIALIZER;
  upb_handlerattr_sethandlerdata(&attr, hd);
  upb_handlers_setstartsubmsg(h, fielddef, startmapentry_handler, &attr);
  upb_handlerattr_uninit(&attr);
}

// Adds handlers to a map-entry msgdef.
static void add_handlers_for_mapentry(const upb_msgdef* msgdef,
                                      upb_handlers* h,
                                      Descriptor* desc) {
  const upb_fielddef* key_field = map_entry_key(msgdef);
  const upb_fielddef* value_field = map_entry_value(msgdef);
  map_handlerdata_t* hd = new_map_handlerdata(0, msgdef, desc);
  upb_handlers_addcleanup(h, hd, free);
  upb_handlerattr attr = UPB_HANDLERATTR_INITIALIZER;
  upb_handlerattr_sethandlerdata(&attr, hd);
  upb_handlers_setendmsg(h, endmap_handler, &attr);

  add_handlers_for_singular_field(
      h, key_field,
      offsetof(map_parse_frame_t, key_storage));
  add_handlers_for_singular_field(
      h, value_field,
      offsetof(map_parse_frame_t, value_storage));
}

// Set up handlers for a oneof field.
static void add_handlers_for_oneof_field(upb_handlers *h,
                                         const upb_fielddef *f,
                                         size_t offset,
                                         size_t oneof_case_offset) {

  upb_handlerattr attr = UPB_HANDLERATTR_INITIALIZER;
  upb_handlerattr_sethandlerdata(
      &attr, newoneofhandlerdata(h, offset, oneof_case_offset, f));

  switch (upb_fielddef_type(f)) {

#define SET_HANDLER(utype, ltype)                                 \
  case utype:                                                     \
    upb_handlers_set##ltype(h, f, oneof##ltype##_handler, &attr); \
    break;

    SET_HANDLER(UPB_TYPE_BOOL,   bool);
    SET_HANDLER(UPB_TYPE_INT32,  int32);
    SET_HANDLER(UPB_TYPE_UINT32, uint32);
    SET_HANDLER(UPB_TYPE_ENUM,   int32);
    SET_HANDLER(UPB_TYPE_FLOAT,  float);
    SET_HANDLER(UPB_TYPE_INT64,  int64);
    SET_HANDLER(UPB_TYPE_UINT64, uint64);
    SET_HANDLER(UPB_TYPE_DOUBLE, double);

#undef SET_HANDLER

    case UPB_TYPE_STRING:
    case UPB_TYPE_BYTES: {
      bool is_bytes = upb_fielddef_type(f) == UPB_TYPE_BYTES;
      upb_handlers_setstartstr(h, f, is_bytes ?
                               oneofbytes_handler : oneofstr_handler,
                               &attr);
      upb_handlers_setstring(h, f, stringdata_handler, NULL);
      break;
    }
    case UPB_TYPE_MESSAGE: {
      upb_handlers_setstartsubmsg(h, f, oneofsubmsg_handler, &attr);
      break;
    }
  }

  upb_handlerattr_uninit(&attr);
}


static void add_handlers_for_message(const void *closure, upb_handlers *h) {
  const upb_msgdef* msgdef = upb_handlers_msgdef(h);
  Descriptor* desc = ruby_to_Descriptor(get_def_obj((void*)msgdef));

  // If this is a mapentry message type, set up a special set of handlers and
  // bail out of the normal (user-defined) message type handling.
  if (upb_msgdef_mapentry(msgdef)) {
    add_handlers_for_mapentry(msgdef, h, desc);
    return;
  }

  // Ensure layout exists. We may be invoked to create handlers for a given
  // message if we are included as a submsg of another message type before our
  // class is actually built, so to work around this, we just create the layout
  // (and handlers, in the class-building function) on-demand.
  if (desc->layout == NULL) {
    desc->layout = create_layout(desc->msgdef);
  }

  upb_msg_field_iter i;
  for (upb_msg_field_begin(&i, desc->msgdef);
       !upb_msg_field_done(&i);
       upb_msg_field_next(&i)) {
    const upb_fielddef *f = upb_msg_iter_field(&i);
    size_t offset = desc->layout->fields[upb_fielddef_index(f)].offset +
        sizeof(MessageHeader);

    if (upb_fielddef_containingoneof(f)) {
      size_t oneof_case_offset =
          desc->layout->fields[upb_fielddef_index(f)].case_offset +
          sizeof(MessageHeader);
      add_handlers_for_oneof_field(h, f, offset, oneof_case_offset);
    } else if (is_map_field(f)) {
      add_handlers_for_mapfield(h, f, offset, desc);
    } else if (upb_fielddef_isseq(f)) {
      add_handlers_for_repeated_field(h, f, offset);
    } else {
      add_handlers_for_singular_field(h, f, offset);
    }
  }
}

// Creates upb handlers for populating a message.
static const upb_handlers *new_fill_handlers(Descriptor* desc,
                                             const void* owner) {
  // TODO(cfallin, haberman): once upb gets a caching/memoization layer for
  // handlers, reuse subdef handlers so that e.g. if we already parse
  // B-with-field-of-type-C, we don't have to rebuild the whole hierarchy to
  // parse A-with-field-of-type-B-with-field-of-type-C.
  return upb_handlers_newfrozen(desc->msgdef, owner,
                                add_handlers_for_message, NULL);
}

// Constructs the handlers for filling a message's data into an in-memory
// object.
const upb_handlers* get_fill_handlers(Descriptor* desc) {
  if (!desc->fill_handlers) {
    desc->fill_handlers =
        new_fill_handlers(desc, &desc->fill_handlers);
  }
  return desc->fill_handlers;
}

// Constructs the upb decoder method for parsing messages of this type.
// This is called from the message class creation code.
const upb_pbdecodermethod *new_fillmsg_decodermethod(Descriptor* desc,
                                                     const void* owner) {
  const upb_handlers* handlers = get_fill_handlers(desc);
  upb_pbdecodermethodopts opts;
  upb_pbdecodermethodopts_init(&opts, handlers);

  const upb_pbdecodermethod *ret = upb_pbdecodermethod_new(&opts, owner);
  return ret;
}

static const upb_pbdecodermethod *msgdef_decodermethod(Descriptor* desc) {
  if (desc->fill_method == NULL) {
    desc->fill_method = new_fillmsg_decodermethod(
        desc, &desc->fill_method);
  }
  return desc->fill_method;
}


// Stack-allocated context during an encode/decode operation. Contains the upb
// environment and its stack-based allocator, an initial buffer for allocations
// to avoid malloc() when possible, and a template for Ruby exception messages
// if any error occurs.
#define STACK_ENV_STACKBYTES 4096
typedef struct {
  upb_env env;
  upb_seededalloc alloc;
  const char* ruby_error_template;
  char allocbuf[STACK_ENV_STACKBYTES];
} stackenv;

static void stackenv_init(stackenv* se, const char* errmsg);
static void stackenv_uninit(stackenv* se);

// Callback invoked by upb if any error occurs during parsing or serialization.
static bool env_error_func(void* ud, const upb_status* status) {
  stackenv* se = ud;
  // Free the env -- rb_raise will longjmp up the stack past the encode/decode
  // function so it would not otherwise have been freed.
  stackenv_uninit(se);
  rb_raise(rb_eRuntimeError, se->ruby_error_template,
           upb_status_errmsg(status));
  // Never reached: rb_raise() always longjmp()s up the stack, past all of our
  // code, back to Ruby.
  return false;
}

static void stackenv_init(stackenv* se, const char* errmsg) {
  se->ruby_error_template = errmsg;
  upb_env_init(&se->env);
  upb_seededalloc_init(&se->alloc, &se->allocbuf, STACK_ENV_STACKBYTES);
  upb_env_setallocfunc(
      &se->env, upb_seededalloc_getallocfunc(&se->alloc), &se->alloc);
  upb_env_seterrorfunc(&se->env, env_error_func, se);
}

static void stackenv_uninit(stackenv* se) {
  upb_env_uninit(&se->env);
  upb_seededalloc_uninit(&se->alloc);
}

/*
 * call-seq:
 *     MessageClass.decode(data) => message
 *
 * Decodes the given data (as a string containing bytes in protocol buffers wire
 * format) under the interpretration given by this message class's definition
 * and returns a message object with the corresponding field values.
 */
VALUE Message_decode(VALUE klass, VALUE data) {
  VALUE descriptor = rb_ivar_get(klass, descriptor_instancevar_interned);
  Descriptor* desc = ruby_to_Descriptor(descriptor);
  VALUE msgklass = Descriptor_msgclass(descriptor);

  if (TYPE(data) != T_STRING) {
    rb_raise(rb_eArgError, "Expected string for binary protobuf data.");
  }

  VALUE msg_rb = rb_class_new_instance(0, NULL, msgklass);
  MessageHeader* msg;
  TypedData_Get_Struct(msg_rb, MessageHeader, &Message_type, msg);

  const upb_pbdecodermethod* method = msgdef_decodermethod(desc);
  const upb_handlers* h = upb_pbdecodermethod_desthandlers(method);
  stackenv se;
  stackenv_init(&se, "Error occurred during parsing: %s");

  upb_sink sink;
  upb_sink_reset(&sink, h, msg);
  upb_pbdecoder* decoder =
      upb_pbdecoder_create(&se.env, method, &sink);
  upb_bufsrc_putbuf(RSTRING_PTR(data), RSTRING_LEN(data),
                    upb_pbdecoder_input(decoder));

  stackenv_uninit(&se);

  return msg_rb;
}

/*
 * call-seq:
 *     MessageClass.decode_json(data) => message
 *
 * Decodes the given data (as a string containing bytes in protocol buffers wire
 * format) under the interpretration given by this message class's definition
 * and returns a message object with the corresponding field values.
 */
VALUE Message_decode_json(VALUE klass, VALUE data) {
  VALUE descriptor = rb_ivar_get(klass, descriptor_instancevar_interned);
  Descriptor* desc = ruby_to_Descriptor(descriptor);
  VALUE msgklass = Descriptor_msgclass(descriptor);

  if (TYPE(data) != T_STRING) {
    rb_raise(rb_eArgError, "Expected string for JSON data.");
  }
  // TODO(cfallin): Check and respect string encoding. If not UTF-8, we need to
  // convert, because string handlers pass data directly to message string
  // fields.

  VALUE msg_rb = rb_class_new_instance(0, NULL, msgklass);
  MessageHeader* msg;
  TypedData_Get_Struct(msg_rb, MessageHeader, &Message_type, msg);

  stackenv se;
  stackenv_init(&se, "Error occurred during parsing: %s");

  upb_sink sink;
  upb_sink_reset(&sink, get_fill_handlers(desc), msg);
  upb_json_parser* parser = upb_json_parser_create(&se.env, &sink);
  upb_bufsrc_putbuf(RSTRING_PTR(data), RSTRING_LEN(data),
                    upb_json_parser_input(parser));

  stackenv_uninit(&se);

  return msg_rb;
}

// -----------------------------------------------------------------------------
// Serializing.
// -----------------------------------------------------------------------------
//
// The code below also comes from upb's prototype Ruby binding, developed by
// haberman@.

/* stringsink *****************************************************************/

// This should probably be factored into a common upb component.

typedef struct {
  upb_byteshandler handler;
  upb_bytessink sink;
  char *ptr;
  size_t len, size;
} stringsink;

static void *stringsink_start(void *_sink, const void *hd, size_t size_hint) {
  stringsink *sink = _sink;
  sink->len = 0;
  return sink;
}

static size_t stringsink_string(void *_sink, const void *hd, const char *ptr,
                                size_t len, const upb_bufhandle *handle) {
  UPB_UNUSED(hd);
  UPB_UNUSED(handle);

  stringsink *sink = _sink;
  size_t new_size = sink->size;

  while (sink->len + len > new_size) {
    new_size *= 2;
  }

  if (new_size != sink->size) {
    sink->ptr = realloc(sink->ptr, new_size);
    sink->size = new_size;
  }

  memcpy(sink->ptr + sink->len, ptr, len);
  sink->len += len;

  return len;
}

void stringsink_init(stringsink *sink) {
  upb_byteshandler_init(&sink->handler);
  upb_byteshandler_setstartstr(&sink->handler, stringsink_start, NULL);
  upb_byteshandler_setstring(&sink->handler, stringsink_string, NULL);

  upb_bytessink_reset(&sink->sink, &sink->handler, sink);

  sink->size = 32;
  sink->ptr = malloc(sink->size);
  sink->len = 0;
}

void stringsink_uninit(stringsink *sink) {
  free(sink->ptr);
}

/* msgvisitor *****************************************************************/

// TODO: If/when we support proto2 semantics in addition to the current proto3
// semantics, which means that we have true field presence, we will want to
// modify msgvisitor so that it emits all present fields rather than all
// non-default-value fields.
//
// Likewise, when implementing JSON serialization, we may need to have a
// 'verbose' mode that outputs all fields and a 'concise' mode that outputs only
// those with non-default values.

static void putmsg(VALUE msg, const Descriptor* desc,
                   upb_sink *sink, int depth);

static upb_selector_t getsel(const upb_fielddef *f, upb_handlertype_t type) {
  upb_selector_t ret;
  bool ok = upb_handlers_getselector(f, type, &ret);
  UPB_ASSERT_VAR(ok, ok);
  return ret;
}

static void putstr(VALUE str, const upb_fielddef *f, upb_sink *sink) {
  if (str == Qnil) return;

  assert(BUILTIN_TYPE(str) == RUBY_T_STRING);
  upb_sink subsink;

  // Ensure that the string has the correct encoding. We also check at field-set
  // time, but the user may have mutated the string object since then.
  native_slot_validate_string_encoding(upb_fielddef_type(f), str);

  upb_sink_startstr(sink, getsel(f, UPB_HANDLER_STARTSTR), RSTRING_LEN(str),
                    &subsink);
  upb_sink_putstring(&subsink, getsel(f, UPB_HANDLER_STRING), RSTRING_PTR(str),
                     RSTRING_LEN(str), NULL);
  upb_sink_endstr(sink, getsel(f, UPB_HANDLER_ENDSTR));
}

static void putsubmsg(VALUE submsg, const upb_fielddef *f, upb_sink *sink,
                      int depth) {
  if (submsg == Qnil) return;

  upb_sink subsink;
  VALUE descriptor = rb_ivar_get(submsg, descriptor_instancevar_interned);
  Descriptor* subdesc = ruby_to_Descriptor(descriptor);

  upb_sink_startsubmsg(sink, getsel(f, UPB_HANDLER_STARTSUBMSG), &subsink);
  putmsg(submsg, subdesc, &subsink, depth + 1);
  upb_sink_endsubmsg(sink, getsel(f, UPB_HANDLER_ENDSUBMSG));
}

static void putary(VALUE ary, const upb_fielddef *f, upb_sink *sink,
                   int depth) {
  if (ary == Qnil) return;

  upb_sink subsink;

  upb_sink_startseq(sink, getsel(f, UPB_HANDLER_STARTSEQ), &subsink);

  upb_fieldtype_t type = upb_fielddef_type(f);
  upb_selector_t sel = 0;
  if (upb_fielddef_isprimitive(f)) {
    sel = getsel(f, upb_handlers_getprimitivehandlertype(f));
  }

  int size = NUM2INT(RepeatedField_length(ary));
  for (int i = 0; i < size; i++) {
    void* memory = RepeatedField_index_native(ary, i);
    switch (type) {
#define T(upbtypeconst, upbtype, ctype)                         \
  case upbtypeconst:                                            \
    upb_sink_put##upbtype(&subsink, sel, *((ctype *)memory));   \
    break;

      T(UPB_TYPE_FLOAT,  float,  float)
      T(UPB_TYPE_DOUBLE, double, double)
      T(UPB_TYPE_BOOL,   bool,   int8_t)
      case UPB_TYPE_ENUM:
      T(UPB_TYPE_INT32,  int32,  int32_t)
      T(UPB_TYPE_UINT32, uint32, uint32_t)
      T(UPB_TYPE_INT64,  int64,  int64_t)
      T(UPB_TYPE_UINT64, uint64, uint64_t)

      case UPB_TYPE_STRING:
      case UPB_TYPE_BYTES:
        putstr(*((VALUE *)memory), f, &subsink);
        break;
      case UPB_TYPE_MESSAGE:
        putsubmsg(*((VALUE *)memory), f, &subsink, depth);
        break;

#undef T

    }
  }
  upb_sink_endseq(sink, getsel(f, UPB_HANDLER_ENDSEQ));
}

static void put_ruby_value(VALUE value,
                           const upb_fielddef *f,
                           VALUE type_class,
                           int depth,
                           upb_sink *sink) {
  upb_selector_t sel = 0;
  if (upb_fielddef_isprimitive(f)) {
    sel = getsel(f, upb_handlers_getprimitivehandlertype(f));
  }

  switch (upb_fielddef_type(f)) {
    case UPB_TYPE_INT32:
      upb_sink_putint32(sink, sel, NUM2INT(value));
      break;
    case UPB_TYPE_INT64:
      upb_sink_putint64(sink, sel, NUM2LL(value));
      break;
    case UPB_TYPE_UINT32:
      upb_sink_putuint32(sink, sel, NUM2UINT(value));
      break;
    case UPB_TYPE_UINT64:
      upb_sink_putuint64(sink, sel, NUM2ULL(value));
      break;
    case UPB_TYPE_FLOAT:
      upb_sink_putfloat(sink, sel, NUM2DBL(value));
      break;
    case UPB_TYPE_DOUBLE:
      upb_sink_putdouble(sink, sel, NUM2DBL(value));
      break;
    case UPB_TYPE_ENUM: {
      if (TYPE(value) == T_SYMBOL) {
        value = rb_funcall(type_class, rb_intern("resolve"), 1, value);
      }
      upb_sink_putint32(sink, sel, NUM2INT(value));
      break;
    }
    case UPB_TYPE_BOOL:
      upb_sink_putbool(sink, sel, value == Qtrue);
      break;
    case UPB_TYPE_STRING:
    case UPB_TYPE_BYTES:
      putstr(value, f, sink);
      break;
    case UPB_TYPE_MESSAGE:
      putsubmsg(value, f, sink, depth);
  }
}

static void putmap(VALUE map, const upb_fielddef *f, upb_sink *sink,
                   int depth) {
  if (map == Qnil) return;
  Map* self = ruby_to_Map(map);

  upb_sink subsink;

  upb_sink_startseq(sink, getsel(f, UPB_HANDLER_STARTSEQ), &subsink);

  assert(upb_fielddef_type(f) == UPB_TYPE_MESSAGE);
  const upb_fielddef* key_field = map_field_key(f);
  const upb_fielddef* value_field = map_field_value(f);

  Map_iter it;
  for (Map_begin(map, &it); !Map_done(&it); Map_next(&it)) {
    VALUE key = Map_iter_key(&it);
    VALUE value = Map_iter_value(&it);

    upb_sink entry_sink;
    upb_sink_startsubmsg(&subsink, getsel(f, UPB_HANDLER_STARTSUBMSG),
                         &entry_sink);
    upb_sink_startmsg(&entry_sink);

    put_ruby_value(key, key_field, Qnil, depth + 1, &entry_sink);
    put_ruby_value(value, value_field, self->value_type_class, depth + 1,
                   &entry_sink);

    upb_status status;
    upb_sink_endmsg(&entry_sink, &status);
    upb_sink_endsubmsg(&subsink, getsel(f, UPB_HANDLER_ENDSUBMSG));
  }

  upb_sink_endseq(sink, getsel(f, UPB_HANDLER_ENDSEQ));
}

static void putmsg(VALUE msg_rb, const Descriptor* desc,
                   upb_sink *sink, int depth) {
  upb_sink_startmsg(sink);

  // Protect against cycles (possible because users may freely reassign message
  // and repeated fields) by imposing a maximum recursion depth.
  if (depth > ENCODE_MAX_NESTING) {
    rb_raise(rb_eRuntimeError,
             "Maximum recursion depth exceeded during encoding.");
  }

  MessageHeader* msg;
  TypedData_Get_Struct(msg_rb, MessageHeader, &Message_type, msg);

  upb_msg_field_iter i;
  for (upb_msg_field_begin(&i, desc->msgdef);
       !upb_msg_field_done(&i);
       upb_msg_field_next(&i)) {
    upb_fielddef *f = upb_msg_iter_field(&i);
    uint32_t offset =
        desc->layout->fields[upb_fielddef_index(f)].offset +
        sizeof(MessageHeader);

    if (upb_fielddef_containingoneof(f)) {
      uint32_t oneof_case_offset =
          desc->layout->fields[upb_fielddef_index(f)].case_offset +
          sizeof(MessageHeader);
      // For a oneof, check that this field is actually present -- skip all the
      // below if not.
      if (DEREF(msg, oneof_case_offset, uint32_t) !=
          upb_fielddef_number(f)) {
        continue;
      }
      // Otherwise, fall through to the appropriate singular-field handler
      // below.
    }

    if (is_map_field(f)) {
      VALUE map = DEREF(msg, offset, VALUE);
      if (map != Qnil) {
        putmap(map, f, sink, depth);
      }
    } else if (upb_fielddef_isseq(f)) {
      VALUE ary = DEREF(msg, offset, VALUE);
      if (ary != Qnil) {
        putary(ary, f, sink, depth);
      }
    } else if (upb_fielddef_isstring(f)) {
      VALUE str = DEREF(msg, offset, VALUE);
      if (RSTRING_LEN(str) > 0) {
        putstr(str, f, sink);
      }
    } else if (upb_fielddef_issubmsg(f)) {
      putsubmsg(DEREF(msg, offset, VALUE), f, sink, depth);
    } else {
      upb_selector_t sel = getsel(f, upb_handlers_getprimitivehandlertype(f));

#define T(upbtypeconst, upbtype, ctype, default_value)                \
  case upbtypeconst: {                                                \
      ctype value = DEREF(msg, offset, ctype);                        \
      if (value != default_value) {                                   \
        upb_sink_put##upbtype(sink, sel, value);                      \
      }                                                               \
    }                                                                 \
    break;

      switch (upb_fielddef_type(f)) {
        T(UPB_TYPE_FLOAT,  float,  float, 0.0)
        T(UPB_TYPE_DOUBLE, double, double, 0.0)
        T(UPB_TYPE_BOOL,   bool,   uint8_t, 0)
        case UPB_TYPE_ENUM:
        T(UPB_TYPE_INT32,  int32,  int32_t, 0)
        T(UPB_TYPE_UINT32, uint32, uint32_t, 0)
        T(UPB_TYPE_INT64,  int64,  int64_t, 0)
        T(UPB_TYPE_UINT64, uint64, uint64_t, 0)

        case UPB_TYPE_STRING:
        case UPB_TYPE_BYTES:
        case UPB_TYPE_MESSAGE: rb_raise(rb_eRuntimeError, "Internal error.");
      }

#undef T

    }
  }

  upb_status status;
  upb_sink_endmsg(sink, &status);
}

static const upb_handlers* msgdef_pb_serialize_handlers(Descriptor* desc) {
  if (desc->pb_serialize_handlers == NULL) {
    desc->pb_serialize_handlers =
        upb_pb_encoder_newhandlers(desc->msgdef, &desc->pb_serialize_handlers);
  }
  return desc->pb_serialize_handlers;
}

static const upb_handlers* msgdef_json_serialize_handlers(Descriptor* desc) {
  if (desc->json_serialize_handlers == NULL) {
    desc->json_serialize_handlers =
        upb_json_printer_newhandlers(
            desc->msgdef, &desc->json_serialize_handlers);
  }
  return desc->json_serialize_handlers;
}

/*
 * call-seq:
 *     MessageClass.encode(msg) => bytes
 *
 * Encodes the given message object to its serialized form in protocol buffers
 * wire format.
 */
VALUE Message_encode(VALUE klass, VALUE msg_rb) {
  VALUE descriptor = rb_ivar_get(klass, descriptor_instancevar_interned);
  Descriptor* desc = ruby_to_Descriptor(descriptor);

  stringsink sink;
  stringsink_init(&sink);

  const upb_handlers* serialize_handlers =
      msgdef_pb_serialize_handlers(desc);

  stackenv se;
  stackenv_init(&se, "Error occurred during encoding: %s");
  upb_pb_encoder* encoder =
      upb_pb_encoder_create(&se.env, serialize_handlers, &sink.sink);

  putmsg(msg_rb, desc, upb_pb_encoder_input(encoder), 0);

  VALUE ret = rb_str_new(sink.ptr, sink.len);

  stackenv_uninit(&se);
  stringsink_uninit(&sink);

  return ret;
}

/*
 * call-seq:
 *     MessageClass.encode_json(msg) => json_string
 *
 * Encodes the given message object into its serialized JSON representation.
 */
VALUE Message_encode_json(VALUE klass, VALUE msg_rb) {
  VALUE descriptor = rb_ivar_get(klass, descriptor_instancevar_interned);
  Descriptor* desc = ruby_to_Descriptor(descriptor);

  stringsink sink;
  stringsink_init(&sink);

  const upb_handlers* serialize_handlers =
      msgdef_json_serialize_handlers(desc);

  stackenv se;
  stackenv_init(&se, "Error occurred during encoding: %s");
  upb_json_printer* printer =
      upb_json_printer_create(&se.env, serialize_handlers, &sink.sink);

  putmsg(msg_rb, desc, upb_json_printer_input(printer), 0);

  VALUE ret = rb_str_new(sink.ptr, sink.len);

  stackenv_uninit(&se);
  stringsink_uninit(&sink);

  return ret;
}

