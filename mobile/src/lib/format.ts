/**
 * Number formatting without relying on Intl (Hermes builds differ):
 *   BDT uses South Asian grouping: ৳6,33,565 (lakh / crore)
 *   CNY uses 3-digit grouping:     ¥35,200
 *   Bengali UI shows Bengali digits: ৳৬,৩৩,৫৬৫
 */
import type { Lang } from './i18n';

const BN_DIGITS = '০১২৩৪৫৬৭৮৯';

export function toBnDigits(s: string): string {
  return s.replace(/[0-9]/g, (d) => BN_DIGITS[Number(d)]);
}

export function localDigits(s: string, lang: Lang): string {
  return lang === 'bn' ? toBnDigits(s) : s;
}

export function groupIndian(intStr: string): string {
  const neg = intStr.startsWith('-');
  const s = neg ? intStr.slice(1) : intStr;
  if (s.length <= 3) return (neg ? '-' : '') + s;
  const last3 = s.slice(-3);
  const rest = s.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ',');
  return (neg ? '-' : '') + rest + ',' + last3;
}

export function group3(intStr: string): string {
  return intStr.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

export function bdt(amount: string | number, lang: Lang): string {
  const n = Math.round(Number(amount));
  return localDigits('৳' + groupIndian(String(n)), lang);
}

export function cny(amount: string | number, lang: Lang): string {
  const n = Number(amount);
  const whole = Number.isInteger(n) ? String(n) : n.toFixed(2);
  const [i, f] = whole.split('.');
  return localDigits('¥' + group3(i) + (f && f !== '00' ? '.' + f : ''), lang);
}

export function num(n: string | number, lang: Lang): string {
  return localDigits(String(n), lang);
}

export function shortDate(iso: string | undefined, lang: Lang): string {
  if (!iso) return '';
  return localDigits(iso.slice(0, 10), lang);
}
