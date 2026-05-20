# Coding Style

## Immutability (CRITICAL)

ALWAYS create new values, NEVER mutate existing ones. Use language-appropriate immutable patterns to derive new state.

## File Organization

MANY SMALL FILES > FEW LARGE FILES:
- High cohesion, low coupling
- 200-400 lines typical, 800 max
- Extract utilities from large modules
- Organize by feature/domain, not by type

## Error Handling

ALWAYS handle errors comprehensively:
- Catch errors at boundaries (API handlers, async tasks)
- Log with sufficient context for debugging
- Re-throw with user-friendly messages
- Never swallow errors silently

## Input Validation

ALWAYS validate user input at system boundaries (API endpoints, form submissions, external data). Use schema validation libraries available in the project's language over manual checks.

## Code Quality Checklist

Before marking work complete:
- [ ] Code is readable and well-named
- [ ] Functions are small (<50 lines)
- [ ] Files are focused (<800 lines)
- [ ] No deep nesting (>4 levels)
- [ ] Proper error handling
- [ ] No debug output statements left in code
- [ ] No hardcoded values
- [ ] No mutation (immutable patterns used)
