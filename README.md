# golangRepoMigration

Herramienta CLI local para migrar repositorios Go en lote, reescribiendo referencias de módulo según un CSV de control y aplicando commits/tags de forma determinista, con salida parseable y política **fail-fast**.

## Objetivo del proyecto

- Ejecutar migraciones de módulos Go (`module_old` → `module_new`) sobre múltiples repositorios locales.
- Controlar el progreso por fila en un CSV (estado y notas).
- Mantener trazabilidad con eventos JSONL y códigos de error parseables.
- Abortar inmediatamente ante cualquier error crítico para evitar estados ambiguos.

## Requisitos

- Python 3.10+ (recomendado 3.12)
- `git` disponible en PATH
- Repositorios clonados localmente bajo una estructura base por organización/repositorio
- Firma GPG funcional para commits firmados (`git commit -S`)

## Formato CSV esperado

El archivo CSV debe tener **exactamente** este header y en este orden:

```csv
bb_repo,gh_repo,module_old,module_new,next_tag,status,notes
```

### Campos

- `bb_repo`: referencia de origen (informativo)
- `gh_repo`: repositorio destino en formato `org/repo` (también acepta URL normalizable)
- `module_old`: módulo Go a reemplazar
- `module_new`: nuevo módulo Go
- `next_tag`: tag a crear cuando hay cambios y commit
- `status`: estado de ejecución de la fila
- `notes`: detalle parseable de resultado/error

### Validaciones fail-fast

- Header distinto al esperado → error inmediato (`ERR_CSV_HEADER_MISMATCH`)
- Campos requeridos vacíos (`bb_repo`, `gh_repo`, `module_old`, `module_new`, `next_tag`) → error inmediato (`ERR_CSV_MISSING_FIELD`)
- `gh_repo` inválido → error inmediato (`ERR_CSV_INVALID_GH_REPO`)

## Flags de la CLI

La herramienta expone estos parámetros:

- `--csv` (requerido): ruta al CSV de migración.
- `--base-dir` (requerido): directorio base que contiene repos locales, con estructura `<base-dir>/<org>/<repo>`.
- `--commit-prefix` (requerido): prefijo del mensaje de commit.
- `--dry-run` (opcional): planifica y reporta sin mutar archivos, sin commits y sin tags.
- `--resume` (opcional): omite filas en estado terminal y continúa desde la primera pendiente.

## Flujo de ejecución y comportamiento fail-fast

1. Parseo/validación de argumentos.
2. Carga y validación estricta del CSV.
3. Resolución de filas a ejecutar (`--resume` afecta esta selección).
4. Preflight global:
   - validación de GPG para commits firmados,
   - existencia de repositorio local,
   - árbol limpio (`git status --porcelain`),
   - inexistencia previa del tag objetivo.
5. Procesamiento fila por fila:
   - reescritura de módulos,
   - commit/tag si hubo cambios (salvo `--dry-run`),
   - persistencia de `status`/`notes` en el CSV.
6. Emisión de eventos JSONL y resumen final.

Si ocurre cualquier error de contrato/preflight/rewrite/git/persistencia, la ejecución **se detiene inmediatamente** y retorna código de salida no cero con mensaje parseable.

## Ejemplo de ejecución

```bash
python -m cli.main \
  --csv ./migration.csv \
  --base-dir /data/repos \
  --commit-prefix "chore: migrate module path" \
  --resume
```

Modo simulación (sin cambios):

```bash
python -m cli.main \
  --csv ./migration.csv \
  --base-dir /data/repos \
  --commit-prefix "chore: migrate module path" \
  --dry-run
```

## Commits firmados GPG y formato del mensaje

- Los commits se crean con firma GPG (`git commit -S`).
- Formato de mensaje aplicado por la herramienta:

```text
<prefix> (<repo>)
```

Ejemplo:

```text
chore: migrate module path (my-service)
```

## Operaciones sobre el mismo CSV: preparar workspace y push

Además de la CLI principal, este repo incluye dos scripts para operar sobre el **mismo CSV**:

```csv
bb_repo,gh_repo,module_old,module_new,next_tag,status,notes
```

### 1) Preparar repos locales desde GHE

Script: `scripts/prepare_repos.sh`

Comportamiento:
- Recorre filas en orden CSV.
- Deriva ruta local como `<base-dir>/<org>/<repo>` desde `gh_repo`.
- Si el repo no existe localmente, clona desde GHE.
- Si ya existe (`.git` presente), no hace `fetch`/`pull`; solo reporta `skip_existing`.
- Crea estructura de carpetas faltante.

Uso SSH (default):

```bash
./scripts/prepare_repos.sh \
  --csv ./migration.csv \
  --base-dir /data/repos \
  --ghe-host ghe.example.com
```

Uso HTTPS:

```bash
./scripts/prepare_repos.sh \
  --csv ./migration.csv \
  --base-dir /data/repos \
  --ghe-host ghe.example.com \
  --https
```

### 2) Push de cambios y tags a remotos

Script: `scripts/push_repos.sh`

Comportamiento:
- Recorre filas en orden CSV.
- Verifica que exista repo local.
- Si la rama actual está por delante de su upstream, ejecuta `git push`.
- Si `next_tag` existe en CSV y la tag existe localmente, ejecuta `git push origin <tag>` (sin recrear tag).
- Soporta fail-fast configurable con `--stop-on-error` (default `true`).
- Emite errores parseables por fila en formato:

```text
ERR_*|message=...|row=...|repo=...
```

Uso:

```bash
./scripts/push_repos.sh \
  --csv ./migration.csv \
  --base-dir /data/repos
```

Continuar aunque falle una fila:

```bash
./scripts/push_repos.sh \
  --csv ./migration.csv \
  --base-dir /data/repos \
  --stop-on-error false
```

## Makefile: targets de conveniencia

Se agregó un `Makefile` mínimo con dos targets:

- `prepare-repos`
- `push-repos`

Variables:
- `CSV` (default: `./migration.csv`)
- `BASE_DIR` (default: `./repos`)
- `GHE_HOST` (requerida para `prepare-repos`)
- `PREPARE_PROTOCOL` (`ssh` default, `https` para `--https`)
- `STOP_ON_ERROR` (`true` default)

Ejemplos:

```bash
make prepare-repos CSV=./migration.csv BASE_DIR=/data/repos GHE_HOST=ghe.example.com
make prepare-repos CSV=./migration.csv BASE_DIR=/data/repos GHE_HOST=ghe.example.com PREPARE_PROTOCOL=https
make push-repos CSV=./migration.csv BASE_DIR=/data/repos
make push-repos CSV=./migration.csv BASE_DIR=/data/repos STOP_ON_ERROR=false
```

## Cómo reanudar tras un fallo

Si una fila quedó en estado terminal por error y necesitas reintentarlo:

1. Edita el CSV y cambia el `status` de la fila desde `failed` a `pending`.
2. (Opcional) limpia/ajusta `notes` para dejar trazabilidad clara.
3. Ejecuta nuevamente con `--resume` para continuar desde la primera fila no terminal.

> Nota operativa: la implementación considera terminales `success`, `no_changes`, `already_applied` y `error`. Si tu flujo usa `failed`/`pending`, mantén una convención consistente en el CSV para que la reanudación sea predecible.
