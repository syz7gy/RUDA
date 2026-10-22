public class ProfesionalBienestar {
    private String rol;
    private int cargaLaboral;
    private int umbralSaturacion;
    private boolean estadoRuderalActivado;
    
    // Se inyecta la Neurona que programaste para la toma de decisiones
    private Neurona motorDecision; 

    public ProfesionalBienestar(String rol, int umbral, Neurona motorDecision) {
        this.rol = rol;
        this.umbralSaturacion = umbral;
        this.motorDecision = motorDecision;
        this.cargaLaboral = 0;
        this.estadoRuderalActivado = false;
    }

    public void recibirCasos(int cantidad, Enjambre enjambre) {
        this.cargaLaboral += cantidad;
        evaluarEstado(enjambre);
    }

    private void evaluarEstado(Enjambre enjambre) {
        // Preparación de datos para tu IA: [Saturación (0 a 1), Sobrecarga Crítica (0 o 1)]
        double saturacion = Math.min((double) cargaLaboral / umbralSaturacion, 1.0);
        double sobrecarga = cargaLaboral > umbralSaturacion ? 1.0 : 0.0;
        double[] contexto = {saturacion, sobrecarga};

        // Tu neurona evalúa las variables y emite una predicción
        int alerta = motorDecision.predecir(contexto);

        if (alerta == 1) {
            System.out.println("  [!] ALERTA LOCAL: " + rol + " saturado. IA activa protocolo de enjambre.");
            // Reasignación descentralizada de tareas sin mando jerárquico
            enjambre.redistribuirCarga(this, cargaLaboral - umbralSaturacion);
            this.cargaLaboral = umbralSaturacion;
        }
    }

    // Resiliencia Ruderal: Activación oportunista para contener emergencias
    public boolean asumirCargaSolidaria(int casosExtra) {
        if (this.cargaLaboral + casosExtra <= umbralSaturacion) {
            this.cargaLaboral += casosExtra;
            this.estadoRuderalActivado = true;
            System.out.println("  -> " + rol + " (Ruderal) asume " + casosExtra + " caso(s) en apoyo.");
            return true;
        }
        return false;
    }

    // Resiliencia Ruderal: Retracción eficiente cuando se estabiliza el entorno
    public void procesarCasos() {
        if (cargaLaboral > 0) cargaLaboral--; // Simula resolución de tareas
        
        if (estadoRuderalActivado && cargaLaboral < umbralSaturacion) {
            estadoRuderalActivado = false;
            System.out.println("  <- " + rol + " estabilizado. Retracción ruderal ejecutada.");
        }
    }

    public String getRol() { return rol; }
    public int getCargaLaboral() { return cargaLaboral; }
}