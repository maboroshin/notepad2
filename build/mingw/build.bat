@ECHO OFF
@rem used for GitHub Actions
@rem adjust path for MSYS2, mingw64, mingw32 and llvm-mingw for local use.

SETLOCAL ENABLEEXTENSIONS
CD /D %~dp0

SET /A "JOB_COUNT=(%NUMBER_OF_PROCESSORS% - 1) | 1"
SET "JOBS=-j%JOB_COUNT%"
SET "CLANG="
SET "UCRT="
SET "COMPILER=x86_64"
SET "TARGET=x86_64"
SET "ACTION="

IF /I "%processor_architecture%" == "AMD64" (
    SET "COMPILER=x86_64"   & SET "TARGET=x86_64"
) ELSE IF /I "%processor_architecture%" == "ARM64" (
    SET "COMPILER=llvm"     & SET "TARGET=aarch64"
) ELSE (
    SET "COMPILER=i686"     & SET "TARGET=i686"
)


:CheckFirstArg
IF /I "%~1" == "" GOTO StartWork
IF /I "%~1" == "x86_64"     SET "COMPILER=x86_64"   & SET "TARGET=x86_64"     & SHIFT & GOTO CheckSecondArg
IF /I "%~1" == "i686"       SET "COMPILER=i686"     & SET "TARGET=i686"       & SHIFT & GOTO CheckSecondArg
IF /I "%~1" == "ucrt"       SET "UCRT=1"            & SET "TARGET=x86_64"     & SHIFT & GOTO CheckSecondArg
IF /I "%~1" == "aarch64"    SET "COMPILER=llvm"     & SET "TARGET=aarch64"    & SHIFT & GOTO CheckSecondArg
IF /I "%~1" == "llvm"       SET "COMPILER=llvm"     & SHIFT & GOTO CheckSecondArg
IF /I "%~1" == "Clang"      SET "CLANG=1"           & SHIFT & GOTO CheckSecondArg
IF /I "%~1" == "AVX2"       SET "TARGET=AVX2"       & SHIFT & GOTO CheckSecondArg


:CheckSecondArg
IF /I "%~1" == "" GOTO StartWork
IF /I "%~1" == "x86_64"     SET "TARGET=x86_64"     & SHIFT & GOTO CheckSecondArg
IF /I "%~1" == "AVX2"       SET "TARGET=AVX2"       & SHIFT & GOTO CheckSecondArg
IF /I "%~1" == "i686"       SET "TARGET=i686"       & SHIFT & GOTO CheckSecondArg
IF /I "%~1" == "aarch64"    SET "TARGET=aarch64"    & SHIFT & GOTO CheckSecondArg
IF /I "%~1" == "Clang"      SET "CLANG=1"           & SHIFT & GOTO CheckSecondArg
IF /I "%~1" == "all"        SET "ACTION=all"        & SHIFT & GOTO CheckSecondArg
IF /I "%~1" == "matepath"   SET "ACTION=matepath"   & SHIFT & GOTO CheckSecondArg
IF /I "%~1" == "scintilla"  SET "ACTION=scintilla"  & SHIFT & GOTO CheckSecondArg
IF /I "%~1" == "notepad4"   SET "ACTION=notepad4"   & SHIFT & GOTO CheckSecondArg
IF /I "%~1" == "clean"      SET "ACTION=clean"      & SHIFT & GOTO CheckSecondArg


:StartWork
IF /I "%COMPILER%" == "x86_64" (CALL :Sub_GCC_x86_64)
IF /I "%COMPILER%" == "i686" (CALL :Sub_GCC_i686)
IF /I "%COMPILER%" == "llvm" (CALL :Sub_llvm_mingw)

ENDLOCAL
EXIT /B


:Sub_GCC_x86_64
IF "%UCRT%" == "1" (
    SET "PATH=C:\msys64\ucrt64\bin;C:\msys64\usr\bin;%PATH%"
) ELSE (
    SET "PATH=C:\msys64\mingw64\bin;C:\msys64\usr\bin;%PATH%"
)
IF /I "%TARGET%" == "AVX2" (
    IF "%CLANG%" == "1" (
        mingw32-make ARCH=AVX2 CLANG=1 LTO=1 %JOBS% %ACTION%
    ) ELSE (
        mingw32-make TRIPLET=x86_64-w64-mingw32 ARCH=AVX2 LTO=1 %JOBS% %ACTION%
    )
) ELSE IF "%UCRT%" == "1" (
    IF "%CLANG%" == "1" (
        mingw32-make CLANG=1 LTO=1 WIN7=1 %JOBS% %ACTION%
    ) ELSE (
        mingw32-make TRIPLET=x86_64-w64-mingw32 LTO=1 WIN7=1 %JOBS% %ACTION%
    )
) ELSE (
    IF "%CLANG%" == "1" (
        mingw32-make CLANG=1 LTO=1 %JOBS% %ACTION%
    ) ELSE (
        mingw32-make TRIPLET=x86_64-w64-mingw32 LTO=1 %JOBS% %ACTION%
    )
)

ENDLOCAL
EXIT /B


:Sub_GCC_i686
SET "PATH=C:\msys64\mingw32\bin;C:\msys64\usr\bin;%PATH%"
IF "%CLANG%" == "1" (
    mingw32-make CLANG=1 LTO=1 %JOBS% %ACTION%
) ELSE (
    mingw32-make TRIPLET=i686-w64-mingw32 LTO=1 %JOBS% %ACTION%
)

ENDLOCAL
EXIT /B


:Sub_llvm_mingw
SET "PATH=C:\llvm-mingw\bin;C:\msys64\usr\bin;%PATH%"
IF /I "%TARGET%" == "AVX2" (
    mingw32-make TRIPLET=x86_64-w64-mingw32 ARCH=AVX2 CLANG=1 LTO=1 %JOBS% %ACTION%
) ELSE (
    mingw32-make TRIPLET=%TARGET%-w64-mingw32 CLANG=1 LTO=1 WIN7=1 %JOBS% %ACTION%
)

ENDLOCAL
EXIT /B
