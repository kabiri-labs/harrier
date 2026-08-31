# Path resolution

Applies to `PTN-RES-01`. Cross-references: ASVS V4.3, CWE-22, CWE-98.

## The fix that works

**Do not build a filesystem path from a request value.** Map an opaque
identifier to a path on the server side — a database row, a fixed table, a
generated key — and let the request name only the identifier. Everything below
is for code that cannot be changed this way yet.

## If a path must be accepted

1. **Resolve first, compare second.** Canonicalise the joined path to an
   absolute one — following symbolic links — and only then check that it is
   inside the permitted base directory. A check performed before resolution is
   checking a string, not a location.
2. **Compare against a resolved base, with a separator.** `"/srv/files"` is a
   prefix of `"/srv/files-backup"`, so a prefix test alone lets a sibling
   directory through.
3. **Decode exactly once, in one place.** Every additional decoding stage after
   the check is a bypass. Where a proxy decodes, the application must not decode
   again.
4. **Reject rather than strip.** A filter that removes `../` can be fed a value
   that becomes `../` after removal. Rejection has no such failure mode, and it
   is also what tells an operator that an attack happened.
5. **Constrain the name, not the path.** Where the value is a filename, allow a
   character set and a maximum length and forbid separators outright. This is a
   whitelist question, and a whitelist is enforceable in a way a blacklist of
   traversal forms is not.

## Reducing what a bypass is worth

- **Never include a path derived from a request value.** Templates and pages
  resolve through a fixed loader with a fixed root, and stream wrappers are
  disabled in production configuration.
- **Serve files as data.** An explicit content type, `Content-Disposition:
  attachment`, and no interpretation of what was read.
- **Give the process nothing to find.** Least privilege, no secrets readable by
  the account serving files, and configuration supplied by the environment
  rather than by a file inside the served tree.

## What does not work

Blacklisting `../`, rejecting requests containing `etc/passwd`, and checking the
extension after concatenation. Each addresses one spelling of the input rather
than the resolution that produced the path, and the encoding table in
`payloads/traversal/encoding.yaml` exists because each has been worked around
for twenty years.
