# KI-TIAN Skills Central

> Todos los skills del ecosistema KI-TIAN en un solo lugar.  
> Compatible con Codex, Open Code, Gemini, GitHub Copilot y otras IA.

---

## 📂 Índice de Skills

| # | Skill | Archivo | Motores |
|---|-------|---------|---------|
| 1 | [Database Project Agent](#1-database-project-agent) | `skills/database-project-agent/SKILL.md` | MySQL, PostgreSQL, SQLite, Firebase, MongoDB |
| 2 | [Web Project Agent](#2-web-project-agent) | `skills/web-project-agent/SKILL.md` | Laravel, Django, Next.js, Flask, NestJS |
| 3 | [Code Architect Agent](#3-code-architect-agent) | `skills/code-architect-agent/SKILL.md` | Python, JS, TypeScript, PHP, C#, Rust |

---

## 1. Database Project Agent

**Ubicación:** `skills/database-project-agent/SKILL.md`  
**Motores:** MySQL, PostgreSQL, SQLite, Firebase Firestore, MongoDB  
**Compatibilidad:** VS Code, Docker, PlanetScale, Supabase, Railway  

El sub-agente de base de datos diseña, gestiona y optimiza bases de datos por proyecto.  
Cubre: diseño de esquema, SQL, migraciones, usuarios, backups, ORMs, Firebase, VS Code y configuración por proyecto.

**Prompt de activación:**
```
Actúa como sub-agente especialista en bases de datos para proyectos.
Analiza el proyecto proporcionado, identifica sus entidades principales,
diseña la base de datos adecuada y genera scripts SQL en MySQL por defecto.
```

---

## 2. Web Project Agent

**Ubicación:** `skills/web-project-agent/SKILL.md`  
**Frameworks:** Laravel, Django, Rails, Next.js, NestJS, Flask, FastAPI  
**Frontend:** React, Vue, Angular, Svelte, HTMX, Alpine  

El sub-agente web analiza proyectos, propone arquitectura frontend/backend, estructura de carpetas, rutas API, autenticación, despliegue y hosting.

**Prompt de activación:**
```
Actúa como sub-agente especialista en proyectos web.
Analiza el proyecto, propón stack tecnológico, estructura de carpetas,
arquitectura de componentes, rutas y plan de despliegue.
```

---

## 3. Code Architect Agent

**Ubicación:** `skills/code-architect-agent/SKILL.md`  
**Lenguajes:** Python, JavaScript, TypeScript, C#, PHP, Rust, Go, Java  

El sub-agente arquitecto revisa código, propone mejoras de estructura, patrones de diseño, refactorización, testing y documentación técnica.

**Prompt de activación:**
```
Actúa como sub-agente arquitecto de código.
Revisa el proyecto, identifica problemas de arquitectura,
propón refactorización y patrones de diseño aplicables.
```

---

## 📁 Estructura de archivos

```
C:\Temp\kitian\skills\
├── SKILLS.md                              ← Este archivo (índice central)
├── database-project-agent/
│   └── SKILL.md                           ← Skill de base de datos
├── web-project-agent/
│   └── SKILL.md                           ← Skill de proyectos web
└── code-architect-agent/
    └── SKILL.md                           ← Skill de arquitectura de código
```

---

## 🚀 Cómo usar

1. Copiá el prompt de activación del skill que necesites
2. Pegalo en Codex, Open Code, Gemini o GitHub Copilot
3. El sub-agente se activa con ese rol y contexto

---

## 📝 Notas

- Todos los skills son compatibles entre sí
- Cada skill puede trabajar con los archivos de configuración generados por otros skills
- Las configuraciones de base de datos se guardan en `GITHUT/[proyecto]/config/db/`
- Para crear un nuevo skill, copiá la estructura de `database-project-agent/`
