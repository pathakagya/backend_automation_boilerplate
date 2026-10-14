# Data Builder Field Classification Checklist

Before writing a factory method, classify **every** field in the sample payload into exactly one
bucket. Each bucket has a fixed rule — don't improvise per-field.

| Bucket | Examples | Rule |
|--------|----------|------|
| **ID** | `customer_id`, `order_id`, any FK reference | Always a **required, explicit kwarg** — never Faker-generated. The caller must supply a real, valid ID; a fabricated one will fail FK constraints or 404 against the real API. |
| **Audit** | `created_by`, `modified_by`, `updated_by` | **Hardcoded to a project constant** (e.g. `"AUTOMATION"`), never Faker, though still overridable via `**overrides` like everything else. |
| **Enum** | `status`, `type`, any field with a fixed value set | An explicit `_VALID_<FIELD>` tuple/dict on the class + `random.choice(...)` — never a Faker-generated string that might not match a real accepted value. |
| **Text** | free-form strings (`notes`, `description`, `name`) | `Faker` (`_faker.sentence()`, `_faker.word()`, `_faker.company()`, ...). |
| **Number** | amounts, quantities, counts | `Faker` (`_faker.pyfloat(...)`, `_faker.pyint(...)`) unless the field has real bounds the API enforces — then constrain the Faker call to those bounds. |
| **Date** | timestamps, due dates, effective dates | `Faker` (`_faker.date()`, `_faker.future_date()`, `_faker.date_time_this_year()`) — format to match what the API actually expects (check a real response first). |

## Before finalizing

- [ ] No real customer/user/loan/account data pasted into the skill invocation or the generated
      file — sample payloads must be sanitized/synthetic before they reach this checklist.
- [ ] Every ID field is a required kwarg with no default.
- [ ] Every enum field has an explicit valid-values list, not a guessed one — verify against real
      API docs, an OpenAPI spec, or an existing response if unsure; don't assume from field name
      alone (e.g. `status` might have 3 values or 12).
- [ ] Audit fields are hardcoded, not Faker.
- [ ] The method ends with `payload.update(overrides)` (or equivalent) so every field remains
      overridable — this is the sole extension mechanism, not conditional branches per variant.
