import { describe, expect, it } from 'vitest';

import {
  assignAvatarColors,
  avatarColor,
  AVATAR_COLORS,
} from '../color-constants';

describe('assignAvatarColors', () => {
  it('maps each id to the avatar color for its position', () => {
    const map = assignAvatarColors(['a', 'b', 'c']);
    expect(map.get('a')).toBe(avatarColor(0));
    expect(map.get('b')).toBe(avatarColor(1));
    expect(map.get('c')).toBe(avatarColor(2));
  });

  it('cycles colors once the palette is exhausted', () => {
    const ids = Array.from({ length: AVATAR_COLORS.length + 1 }, (_, i) =>
      String(i),
    );
    const map = assignAvatarColors(ids);
    expect(map.get(String(AVATAR_COLORS.length))).toBe(avatarColor(0));
  });

  it('returns an empty map for no ids', () => {
    expect(assignAvatarColors([]).size).toBe(0);
  });
});
