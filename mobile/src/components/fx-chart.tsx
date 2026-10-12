import { View } from 'react-native';
import Svg, { Circle, Polyline } from 'react-native-svg';

import { Muted, Row, styles } from '@/components/ui';
import { Brand } from '@/constants/theme';
import type { FxPoint } from '@/lib/api';
import type { Lang } from '@/lib/i18n';
import { localDigits, shortDate } from '@/lib/format';

/** Minimal line chart of BDT per CNY. Real data only; no forecast line is drawn on purpose. */
export function FxChart({ points, lang, height = 90 }: { points: FxPoint[]; lang: Lang; height?: number }) {
  if (points.length < 2) return null;
  const width = 300;
  const values = points.map((p) => p.bdt_per_cny);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const xy = values.map((v, i) => [(i / (values.length - 1)) * width, height - 6 - ((v - min) / span) * (height - 12)]);
  const last = xy[xy.length - 1];
  return (
    <View>
      <Svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <Polyline points={xy.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ')} fill="none" stroke={Brand.primary} strokeWidth={2} />
        <Circle cx={last[0]} cy={last[1]} r={4} fill={Brand.primary} />
      </Svg>
      <Row style={styles.between}>
        <Muted>{shortDate(points[0].date, lang)}</Muted>
        <Muted>
          {localDigits(`৳${min.toFixed(2)} – ৳${max.toFixed(2)}`, lang)}
        </Muted>
        <Muted>{shortDate(points[points.length - 1].date, lang)}</Muted>
      </Row>
    </View>
  );
}
