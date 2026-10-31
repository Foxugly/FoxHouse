// Les tests lisent le disque (images des cartes, sources du tapis) : seul ce morceau de Node est typé.
declare module 'node:fs' {
  export function existsSync(chemin: string): boolean;
  export function readdirSync(chemin: string): string[];
  export function readFileSync(chemin: string, encodage: 'utf8'): string;
  export function statSync(chemin: string): { isDirectory(): boolean };
}
