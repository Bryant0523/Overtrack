import unittest
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO
from utils.procesamiento import calcular_extras, procesar_registros, validar_calculo

class TestCalculoHorasExtras(unittest.TestCase):
    def test_calcular_extras_sin_tardanza_no_extras(self):
        entrada_dt = datetime(2026, 6, 22, 8, 0)
        salida_dt = datetime(2026, 6, 22, 17, 0)
        entrada_oficial = datetime(2026, 6, 22, 8, 0)
        salida_oficial = datetime(2026, 6, 22, 17, 0)
        tardanza = entrada_dt - entrada_oficial
        self.assertEqual(
            calcular_extras(
                entrada_dt, salida_dt, entrada_oficial, salida_oficial,
                tardanza, umbral_extras_minutos=30
            ).total_seconds(),
            0
        )

    def test_calcular_extras_sin_tardanza_umbral_exacto(self):
        entrada_dt = datetime(2026, 6, 22, 8, 0)
        salida_dt = datetime(2026, 6, 22, 17, 30)
        entrada_oficial = datetime(2026, 6, 22, 8, 0)
        salida_oficial = datetime(2026, 6, 22, 17, 0)
        tardanza = entrada_dt - entrada_oficial
        self.assertEqual(
            calcular_extras(
                entrada_dt, salida_dt, entrada_oficial, salida_oficial,
                tardanza, umbral_extras_minutos=30
            ).total_seconds(),
            30 * 60
        )

    def test_calcular_extras_con_tardanza_resta_a_extras(self):
        entrada_dt = datetime(2026, 6, 22, 8, 10)
        salida_dt = datetime(2026, 6, 22, 18, 0)
        entrada_oficial = datetime(2026, 6, 22, 8, 0)
        salida_oficial = datetime(2026, 6, 22, 17, 0)
        tardanza = entrada_dt - entrada_oficial
        self.assertEqual(
            calcular_extras(
                entrada_dt, salida_dt, entrada_oficial, salida_oficial,
                tardanza, umbral_extras_minutos=30
            ).total_seconds(),
            50 * 60
        )

    def test_calcular_extras_con_tardanza_que_no_supera_umbral(self):
        entrada_dt = datetime(2026, 6, 22, 8, 15)
        salida_dt = datetime(2026, 6, 22, 17, 30)
        entrada_oficial = datetime(2026, 6, 22, 8, 0)
        salida_oficial = datetime(2026, 6, 22, 17, 0)
        tardanza = entrada_dt - entrada_oficial
        self.assertEqual(
            calcular_extras(
                entrada_dt, salida_dt, entrada_oficial, salida_oficial,
                tardanza, umbral_extras_minutos=30
            ).total_seconds(),
            0
        )

    def test_procesar_registros_aplica_umbral_en_dataframe(self):
        df = pd.DataFrame([
            [None, "Juan Pardo", None, "2026-06-22 08:10:00"],
            [None, "Juan Pardo", None, "2026-06-22 18:00:00"],
        ], columns=["X", "Nombre", "Y", "FechaHora"])
        resultado = procesar_registros(df, "medellin", umbral_extras_minutos=30)
        self.assertEqual(len(resultado), 2)
        fila = resultado.iloc[0]
        self.assertEqual(fila["Tardanza"], "00h 10m")
        self.assertEqual(fila["Horas extras"], "00h 50m")

    def test_procesar_registros_no_extras_por_umbral(self):
        df = pd.DataFrame([
            [None, "Ana Perez", None, "2026-06-22 08:15:00"],
            [None, "Ana Perez", None, "2026-06-22 17:20:00"],
        ], columns=["A", "Nombre", "C", "Registro"])
        resultado = procesar_registros(df, "medellin", umbral_extras_minutos=30)
        self.assertEqual(len(resultado), 2)
        fila = resultado.iloc[0]
        self.assertEqual(fila["Tardanza"], "00h 15m")
        self.assertEqual(fila["Horas extras"], "00h 00m")

    def test_validar_calculo_retorna_ok_para_resultado_consistente(self):
        estado, detalle = validar_calculo(
            entrada_dt=datetime(2026, 6, 22, 8, 10),
            salida_dt=datetime(2026, 6, 22, 18, 0),
            entrada_oficial_dt=datetime(2026, 6, 22, 8, 0),
            salida_oficial_dt=datetime(2026, 6, 22, 17, 0),
            tardanza_td=timedelta(minutes=10),
            tiempo_almuerzo_td=timedelta(minutes=60),
            horas_trab_td=timedelta(hours=8, minutes=50),
            extras_td=timedelta(minutes=50),
            umbral_extras_minutos=30,
        )
        self.assertEqual(estado, "OK")
        self.assertIn("consistente", detalle.lower())

    def test_validar_calculo_retorna_revisar_si_hay_desajuste(self):
        estado, detalle = validar_calculo(
            entrada_dt=datetime(2026, 6, 22, 8, 0),
            salida_dt=datetime(2026, 6, 22, 17, 0),
            entrada_oficial_dt=datetime(2026, 6, 22, 8, 0),
            salida_oficial_dt=datetime(2026, 6, 22, 17, 0),
            tardanza_td=timedelta(0),
            tiempo_almuerzo_td=timedelta(minutes=60),
            horas_trab_td=timedelta(hours=8),
            extras_td=timedelta(minutes=30),
            umbral_extras_minutos=30,
        )
        self.assertEqual(estado, "Revisar")
        self.assertIn("esperado", detalle.lower())

    def test_validar_calculo_retorna_revisar_por_salida_temprana_con_permiso(self):
        estado, detalle = validar_calculo(
            entrada_dt=datetime(2026, 6, 22, 6, 45),
            salida_dt=datetime(2026, 6, 22, 14, 6),
            entrada_oficial_dt=datetime(2026, 6, 22, 8, 0),
            salida_oficial_dt=datetime(2026, 6, 22, 17, 0),
            tardanza_td=timedelta(0),
            tiempo_almuerzo_td=timedelta(minutes=60),
            horas_trab_td=timedelta(hours=6, minutes=20),
            extras_td=timedelta(minutes=74),
            umbral_extras_minutos=30,
            permiso_salida_temprana=True,
        )
        self.assertEqual(estado, "Revisar")
        self.assertIn("permiso", detalle.lower())

    def test_procesar_registros_csv_integration_early_and_late(self):
        csv_data = """Dummy,Nombre,Other,FechaHora
x,Juan Pardo,y,2026-06-22 07:45:00
x,Juan Pardo,y,2026-06-22 18:15:00
x,Juan Pardo,y,2026-06-23 07:50:00
x,Juan Pardo,y,2026-06-23 19:10:00
"""
        df = pd.read_csv(StringIO(csv_data))
        resultado = procesar_registros(df, "medellin", umbral_extras_minutos=30)
        self.assertEqual(len(resultado), 3)

        filas_normales = resultado[~resultado["Nombre"].str.contains("TOTAL HORAS EXTRAS", na=False)]
        self.assertEqual(filas_normales.iloc[0]["Nombre"], "Juan Pardo")
        self.assertEqual(filas_normales.iloc[0]["Horas extras"], "01h 30m")
        self.assertEqual(filas_normales.iloc[1]["Horas extras"], "02h 20m")

        fila_total = resultado[resultado["Nombre"].str.contains("TOTAL HORAS EXTRAS", na=False)].iloc[0]
        self.assertEqual(fila_total["Horas extras"], "03h 50m")

if __name__ == "__main__":
    unittest.main()
