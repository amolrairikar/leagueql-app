## Decision

Default `memberId` to `None` per pick when collecting ESPN draft picks (`setdefault`), rather than changing the SQL. DuckDB infers the column from the pick dicts, so guaranteeing the key guarantees the column; existing `memberId` values are untouched. Yahoo already emits `NULL AS member_id`, and no frontend view reads the field, so a null is already a supported value end to end.
