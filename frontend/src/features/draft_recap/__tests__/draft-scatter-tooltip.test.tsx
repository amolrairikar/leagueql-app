import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { DraftScatterPoint } from '../compute-draft-scatter';
import { DraftScatterTooltip } from '../draft-scatter-chart';

const point: DraftScatterPoint = {
  pick: 7,
  points: 248.6,
  player: 'Pat Quarterback',
  manager: 'Alice',
  position: 'QB',
};

describe('DraftScatterTooltip', () => {
  it('shows the player, drafting manager, points, and draft position', () => {
    render(<DraftScatterTooltip active payload={[{ payload: point }]} />);

    expect(screen.getByText('Pat Quarterback')).toBeInTheDocument();
    expect(screen.getByText('Drafted by Alice')).toBeInTheDocument();
    expect(screen.getByText('248.6')).toBeInTheDocument();
    expect(screen.getByText('#7')).toBeInTheDocument();
  });

  it('renders nothing when inactive or without a payload', () => {
    const { container: inactive } = render(
      <DraftScatterTooltip active={false} payload={[{ payload: point }]} />,
    );
    expect(inactive).toBeEmptyDOMElement();

    const { container: empty } = render(
      <DraftScatterTooltip active payload={[]} />,
    );
    expect(empty).toBeEmptyDOMElement();
  });
});
