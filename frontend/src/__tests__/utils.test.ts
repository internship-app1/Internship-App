/**
 * Tests for pure utility logic that doesn't depend on external services.
 * Add more tests here as utility modules are created.
 */

// ---------------------------------------------------------------------------
// Skill badge colour logic (inline — representative of UI helper functions)
// ---------------------------------------------------------------------------

/**
 * Mirrors the colour-selection logic in JobCard.tsx so we can test it in
 * isolation without rendering the full component.
 */
function getSkillColor(index: number): string {
  const colors = [
    'bg-blue-100 text-blue-800',
    'bg-green-100 text-green-800',
    'bg-purple-100 text-purple-800',
    'bg-yellow-100 text-yellow-800',
    'bg-red-100 text-red-800',
  ];
  return colors[index % colors.length];
}

describe('getSkillColor', () => {
  it('returns a non-empty string', () => {
    expect(getSkillColor(0)).toBeTruthy();
  });

  it('cycles through colours', () => {
    const c0 = getSkillColor(0);
    const c5 = getSkillColor(5);
    expect(c0).toBe(c5); // 5 % 5 === 0
  });

  it('different indices give different colours', () => {
    expect(getSkillColor(0)).not.toBe(getSkillColor(1));
  });
});

// ---------------------------------------------------------------------------
// Match score formatting
// ---------------------------------------------------------------------------

function formatMatchScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

describe('formatMatchScore', () => {
  it('converts 1.0 to 100%', () => {
    expect(formatMatchScore(1.0)).toBe('100%');
  });

  it('converts 0.75 to 75%', () => {
    expect(formatMatchScore(0.75)).toBe('75%');
  });

  it('rounds correctly', () => {
    expect(formatMatchScore(0.756)).toBe('76%');
  });
});

export {};
