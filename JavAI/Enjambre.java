import java.util.ArrayList;
import java.util.List;

public class Enjambre {
    private List<ProfesionalBienestar> colmena;

    public Enjambre() {
        this.colmena = new ArrayList<>();
    }

    public void agregarProfesional(ProfesionalBienestar p) {
        colmena.add(p);
    }

    // Inteligencia de Enjambre: Coordinación ante perturbaciones
    public void redistribuirCarga(ProfesionalBienestar origen, int exceso) {
        int casosRestantes = exceso;
        
        for (ProfesionalBienestar compañero : colmena) {
            if (compañero != origen && casosRestantes > 0) {
                if (compañero.asumirCargaSolidaria(1)) {
                    casosRestantes--;
                }
            }
        }
        
        // Si el enjambre no puede contener la crisis, impacta directamente los indicadores de continuidad operativa
        if (casosRestantes > 0) {
            System.out.println("  [x] FALLO SISTÉMICO: " + casosRestantes + " casos represados (Impacto negativo en RTO/RPO).");
        }
    }

    public void avanzarTiempo() {
        for (ProfesionalBienestar p : colmena) {
            p.procesarCasos();
        }
    }

    public void imprimirEstado() {
        System.out.print("Estado Operativo: ");
        for (ProfesionalBienestar p : colmena) {
            System.out.print("[" + p.getRol() + ": " + p.getCargaLaboral() + "] ");
        }
        System.out.println("\n-------------------------------------------------");
    }

    public void setColmena(List<ProfesionalBienestar> colmena) {
        this.colmena = colmena;
    }

    public List<ProfesionalBienestar> getColmena() {
        return colmena;
    }
}