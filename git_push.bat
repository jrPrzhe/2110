@echo off
chcp 65001 >nul
echo Pushing to GitHub...

git remote remove origin 2>nul
git remote add origin https://github.com/jrPrzhe/2110.git
git branch -M main
git push -u origin main

pause


