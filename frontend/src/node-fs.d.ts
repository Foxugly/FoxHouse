// Les tests lisent le disque (vérifier que les images existent) : seul ce morceau de Node est typé.
declare module 'node:fs' {
  export function existsSync(chemin: string): boolean;
  export function readdirSync(chemin: string): string[];
}
