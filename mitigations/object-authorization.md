# Object-level authorization

Applies to `HRR-ACL-02`. Cross-references: ASVS V8.2, V8.3, CWE-639, CWE-566.

## The fix that works

**Authorize the object, not the route.** A check that asks *may this caller
reach this endpoint* answers a question nobody was attacking. The question is
*may this caller reach this record*, and it can only be answered where the
record is, with the caller's identity in hand.

The shape that holds:

```
load the object by its identifier
  → ask whether this principal may perform this operation on this object
    → refuse before anything is read, rendered, or written
```

Two properties of that shape matter more than where it lives:

- **The principal comes from the session, never from the request.** A user id, a
  tenant, an organisation, a role — if the caller sends it, the caller chooses
  it. `CWE-639` is precisely this: the key is user-controlled.
- **The check reads the object being acted on.** A check keyed on a path segment
  misses an identifier that travelled in the body; a check on the record being
  displayed misses the record being written.

## Enforce at the data-access layer

Put the check where the store is reached, not in each handler.

A handler-level check is correct exactly as long as somebody remembers to write
it, and the topic's whole finding is that somebody did not: the export route,
the batch endpoint, the administrative screen, the API added beside the page.
Every one of those is a new handler reading an old store.

The mechanisms that survive a new route being added by somebody who has not read
this document:

- **A scoped accessor.** The only way to load an object takes the principal and
  applies the predicate itself. There is no unscoped `find_by_id` for a new
  handler to reach for, because it does not exist.
- **Row-level security in the database.** The predicate is attached to the
  table, and the session's principal is set on the connection. A route that
  forgets the check gets an empty result rather than somebody else's record.
- **A policy object per resource type**, consulted by a middleware that fails
  closed on any route that did not declare one. The failure mode of a forgotten
  check becomes a broken route rather than a silent disclosure.

**Derive tenancy from the session.** A tenant in a header, a subdomain, a path
prefix or a body field is a tenant the caller picked. Resolve it once at
authentication and let nothing downstream take it from the request.

**Scope lists and exports by the principal, not by a client-supplied filter.**
A list route that returns everything and relies on the client sending
`?owner=me` is not scoped; it is unscoped with a convention. Remove the filter
and it returns the space.

## Reducing what a bypass is worth

**Unguessable identifiers reduce exposure and are not an authorization
control.** They raise the cost of finding a valid identifier, which is worth
having — and they do nothing whatever once one is known, and identifiers leak
constantly: in shared links, notification emails, webhook payloads, exports,
audit trails, and in responses to the very users the object is being hidden
from.

So: use a random identifier where you can, and never let its presence be the
reason a check was not written. An application with UUIDs everywhere and no
ownership check is one leaked link away from the same finding.

If identifiers are sequential today, treat that as a separate, lower-priority
item: it is exposure surface, not the defect.

## What does not work

**Checking in the interface.** Hiding the edit button changes what a browser
renders and nothing about what the endpoint accepts. This is the control the
topic's `-WRITE` unit most often finds to be the only one.

**Checking on read but not on write.** The two paths were frequently written at
different times, and creation in particular tends to *assign* ownership rather
than check it — so the check that refuses an update may have no counterpart on
create at all.

**Relying on identifier entropy.** Covered above, and stated separately here
because it is the reason given most often for the absence of a check.

**A check that runs after the work.** Loading the object, rendering it, and then
deciding whether the caller was allowed to see it leaves the data in a response
buffer, a log line, a cache entry, or an error page. Refuse first.

**Validating that the identifier is well-formed.** A syntactically valid
identifier belonging to somebody else is the entire attack.
