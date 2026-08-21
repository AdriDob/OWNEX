# Generar Instalador Windows .exe

## Opción 1: Desde Windows (Recomendado)

### Prerrequisitos
1. Copiar el proyecto a Windows (o usar `\\wsl.localhost\Ubuntu\home\adri\projects\Rastro`)
2. Instalar NSIS: https://nsis.sourceforge.io/Download/
3. Verificar que el bundle PyInstaller existe: `dist\OWNEX-Desktop-Alpha\OWNEX-Desktop-Alpha.exe`

### Pasos

```batch
# Abrir PowerShell o CMD en el directorio del proyecto
cd installer
BUILD_WINDOWS_EXE.bat
```

O manualmente:

```batch
# Desde la raíz del proyecto
makensis installer\OWNEX-Desktop-Alpha.nsi
```

El instalador se generará como: `OWNEX-Desktop-Alpha-Setup.exe`

### Verificación

```batch
# 1. Ejecutar el instalador
OWNEX-Desktop-Alpha-Setup.exe

# 2. Verificar instalación
dir "%LOCALAPPDATA%\Programs\OWNEX"

# 3. Verificar acceso directo
dir "%APPDATA%\Microsoft\Windows\Start Menu\Programs"
```

## Opción 2: Desde WSL con Wine

### Instalar Wine y NSIS

```bash
sudo apt update
sudo apt install -y wine nsis
```

### Generar instalador

```bash
cd /home/adri/projects/Rastro
makensis installer/OWNEX-Desktop-Alpha.nsi
```

El instalador se generará como: `OWNEX-Desktop-Alpha-Setup.exe`

### Transferir a Windows

```bash
# Copiar a una carpeta accesible desde Windows
cp OWNEX-Desktop-Alpha-Setup.exe /mnt/c/Users/$USER/Desktop/
```

## Opción 3: Script Automatizado

Usar el script `installer/BUILD_WINDOWS_EXE.bat` que:
1. Verifica que makensis esté instalado
2. Verifica que el bundle PyInstaller exista
3. Ejecuta makensis
4. Muestra instrucciones de verificación

## Verificación del Instalador

```batch
# Verificar firma (si está firmado)
signtool verify /pa OWNEX-Desktop-Alpha-Setup.exe

# Verificar contenido
7z l OWNEX-Desktop-Alpha-Setup.exe
```

## Troubleshooting

### makensis no encontrado
- Instalar NSIS desde https://nsis.sourceforge.io/
- Agregar a PATH: `C:\Program Files (x86)\NSIS`

### Bundle no encontrado
- Ejecutar primero: `python -m PyInstaller OWNEX-Desktop-Alpha.spec`
- Verificar que `dist/OWNEX-Desktop-Alpha/` exista

### Errores de permisos
- Ejecutar como Administrador si es necesario
- Verificar acceso a `dist/` y `installer/`

## Estado Actual

- ✅ Script NSIS listo: `installer/OWNEX-Desktop-Alpha.nsi`
- ✅ Bundle PyInstaller listo: `dist/OWNEX-Desktop-Alpha/` (55MB)
- ⏳ Instalador .exe pendiente de generación
