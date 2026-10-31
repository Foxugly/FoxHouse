import { ErrorHandler } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';
import { appConfig } from './app.config';
import { SentryErrorHandler } from './core/sentry';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([])],
    }).compileComponents();
  });

  it('démarre et affiche le <router-outlet>', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const racine = fixture.nativeElement as HTMLElement;
    expect(racine.querySelector('router-outlet')).not.toBeNull();
  });
});

describe('appConfig', () => {
  it('remet les erreurs non gérées à SentryErrorHandler', () => {
    TestBed.configureTestingModule({ providers: appConfig.providers });
    expect(TestBed.inject(ErrorHandler)).toBeInstanceOf(SentryErrorHandler);
  });
});
