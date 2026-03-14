## Summary

<!-- Provide a concise description of the changes in this PR. What problem does it solve, and why is this change needed? -->

**Ticket / Issue:** <!-- e.g. JIRA-123 or #456 -->

**Type of change:**
- [ ] 🐛 Bug fix
- [ ] ✨ New feature
- [ ] ♻️ Refactor
- [ ] 🏗️ Infrastructure / DevOps
- [ ] 📝 Documentation
- [ ] ⚡ Performance improvement
- [ ] 🔒 Security fix

---

## Affected Layers

Check all layers touched by this PR:

- [ ] **Infrastructure** — Terraform, Kubernetes, CI/CD, cloud resources, networking
- [ ] **Backend** — API endpoints, services, database migrations, authentication
- [ ] **Business Logic** — Domain models, rules engine, data processing, integrations
- [ ] **Frontend** — UI components, routing, state management, styling

---

## Infrastructure Changes
<!-- Remove section if not applicable -->

**Resources modified:**
<!-- e.g. "Added S3 bucket for user-uploaded assets; updated IAM role to allow EC2 read access" -->

**Environment impact:**
- [ ] Dev only
- [ ] Staging
- [ ] Production

**Deployment steps / manual actions required:**
```
# e.g.
# terraform apply -target=module.storage
# kubectl rollout restart deployment/api
```

**Rollback plan:**
<!-- How do we undo this if something goes wrong? -->

---

## Backend Changes
<!-- Remove section if not applicable -->

**Endpoints added / modified / removed:**
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/v1/...` | |

**Database migrations:**
- [ ] No migrations
- [ ] Additive migration (safe to deploy before code)
- [ ] Destructive migration (requires coordination) — describe strategy below

```
Migration notes:
```

**Breaking API changes:**
- [ ] No breaking changes
- [ ] Breaking change — consumers notified / versioned endpoint added

---

## Onboarding Logic Changes
<!-- Remove section if not applicable -->

**Domain / rules affected:**
<!-- e.g. "Updated pricing calculation to apply volume discounts before tax" -->
- 
- 

**Edge cases considered:**
<!-- e.g. "Updated pricing calculation to apply volume discounts before tax" -->
- 
- 

---

## Frontend Changes
<!-- Remove section if not applicable -->

**Components added / modified:**
<!-- e.g. "New <UserAvatarMenu> component; updated <CheckoutForm> validation" -->

**Screenshots / recordings:**


**Browser / device testing:**
- [ ] Chrome
- [ ] Firefox
- [ ] Safari
- [ ] Mobile (iOS / Android)

**Accessibility:**
- [ ] No interactive elements changed
- [ ] Keyboard navigation tested
- [ ] Screen reader tested
- [ ] Color contrast verified

---

## Testing

**Tests added / updated:**
- [ ] Unit tests
- [ ] Integration tests
- [ ] E2E tests
- [ ] No tests needed — explain: 

**How to test manually:**
```
1. 
2. 
3. Expected result:
```

**Test coverage delta:** <!-- e.g. "Coverage: 74% → 77%" or "N/A" -->

---

## Security & Compliance

- [ ] No sensitive data exposed in logs or responses
- [ ] Input validation / sanitization applied where needed
- [ ] Authentication / authorization checks in place
- [ ] Dependencies audited (`npm audit` / `pip audit` / etc.)
- [ ] Secrets are in environment variables, not hardcoded

---

## Performance

- [ ] No significant performance impact
- [ ] Load / stress tested — results: 
- [ ] Caching strategy considered
- [ ] Database queries reviewed (N+1, missing indexes, etc.)

---

## Checklist Before Merging

- [ ] Self-reviewed the diff
- [ ] PR title follows [conventional commits](https://www.conventionalcommits.org/) format
- [ ] CHANGELOG / release notes updated (if applicable)
- [ ] Feature flag added for gradual rollout (if applicable)
