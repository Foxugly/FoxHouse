import { scrubUrl } from './sentry';

describe('scrubUrl', () => {
  it('masque token/uid/code en query et en fragment', () => {
    expect(scrubUrl('https://www.foxugly.com/admin/magic#token=abc.def')).toBe(
      'https://www.foxugly.com/admin/magic#token=[Filtered]',
    );
    expect(scrubUrl('/admin/magic?token=abc&x=1')).toBe('/admin/magic?token=[Filtered]&x=1');
    expect(scrubUrl('/r?uid=12&code=zz')).toBe('/r?uid=[Filtered]&code=[Filtered]');
  });

  it('laisse les autres URLs intactes', () => {
    expect(scrubUrl('/accueil?page=2')).toBe('/accueil?page=2');
  });
});
