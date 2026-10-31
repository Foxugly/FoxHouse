import { scrubUrl } from './sentry';

describe('scrubUrl', () => {
  it('masque token/uid/code en query et en fragment', () => {
    expect(scrubUrl('https://foxhouse.foxugly.com/partie/42#token=abc.def')).toBe(
      'https://foxhouse.foxugly.com/partie/42#token=[Filtered]',
    );
    expect(scrubUrl('/partie/42?token=abc&x=1')).toBe('/partie/42?token=[Filtered]&x=1');
    expect(scrubUrl('/r?uid=12&code=zz')).toBe('/r?uid=[Filtered]&code=[Filtered]');
  });

  it('laisse les autres URLs intactes', () => {
    expect(scrubUrl('/accueil?page=2')).toBe('/accueil?page=2');
  });
});
