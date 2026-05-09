# Laboratorio 4 - Round Robin en Python

Este proyecto implementa una simulacion con interfaz grafica del algoritmo de planificacion `Round Robin`.

## Estructura

- `round_robin.py`: punto de entrada para ejecutar la aplicacion.
- `rr_frontend.py`: interfaz grafica construida con `tkinter`.
- `rr_backend.py`: logica de simulacion, estructuras de datos y calculo de metricas.

## Requisitos cubiertos

- Solicita el total de procesos.
- Solicita el tiempo de llegada de cada proceso.
- Permite ingresar la tabla completa de cada proceso con llegada y rafagas alternadas de `CPU` y `E/S`.
- Solicita el tamano del quantum.
- Solicita el tamano del intercambio.
- Muestra la cola de procesos en estado listo.
- Muestra un diagrama de Gantt en pantalla.
- Calcula tiempos de retorno, espera y sus promedios.
- Valida los datos ingresados.
- Representa los resultados en tablas y grafica de tiempo.

## Suposiciones usadas

La interfaz permite cargar directamente las rafagas reales de cada proceso, con una estructura parecida a la prueba de escritorio del tablero:

- `Proceso`
- `T. llegada`
- `CPU 1`
- `E/S 1`
- `CPU 2`
- `E/S 2`
- `CPU 3`

Si necesitas mas columnas de CPU, la app las genera desde el campo `Columnas CPU`.

## Ejecucion

```bash
python round_robin.py
```

## Vista de la aplicacion

- Panel para definir cantidad de procesos, quantum, intercambio y cantidad de columnas CPU.
- Tabla editable tipo pizarra para ingresar llegada y rafagas `CPU / E/S / CPU`.
- Diagrama de Gantt dibujado graficamente.
- Tabla de eventos de la cola de listos.
- Tabla de metricas por proceso con promedios.

## Formulas usadas

- `Tiempo de vuelta = tiempo de finalizacion - tiempo de llegada - tiempo total de E/S`
- `Tiempo de espera = primera entrada a CPU - tiempo de llegada`
