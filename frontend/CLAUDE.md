# Frontend Development Rules

Build the simplest implementation that satisfies the current product requirement.

Do not add abstractions, configuration, components, states, props, animation,
or future-facing functionality unless the current requirement needs them.

Design for the actual user workflow first.

## UI

- Reuse existing components before creating new ones.
- Use shadcn primitives where they fit.
- Custom-build product-specific UI when appropriate.
- Use Motion only when animation improves feedback, hierarchy, or comprehension.
- Do not animate merely for decoration.
- Keep visual hierarchy obvious.
- Keep spacing, typography, radii, and interaction states consistent.
- Support desktop and responsive layouts.
- Maintain accessibility.

## Avoid

- generic AI SaaS appearance
- gradients everywhere
- excessive cards
- excessive rounded boxes
- unnecessary shadows
- unnecessary animations
- giant hero-style typography inside application screens
- decorative elements without product purpose
- creating generic component systems for hypothetical future needs
- redesigning unrelated areas

## Implementation workflow

Before changing a screen:

1. Inspect the current implementation.
2. Understand the product requirement.
3. Identify what can be reused.
4. Design the smallest appropriate solution.
5. Implement it.
6. Run the application.
7. Inspect the real rendered result.
8. Check responsive behavior.
9. Fix actual visual/interaction problems.
10. Stop when the requirement is satisfied.
