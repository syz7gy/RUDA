public class SimuladorBienestar {
    public static void main(String[] args) {
        System.out.println("--- FASE 1: ENTRENANDO IA DE LOS AGENTES ---");
        // Entrenamos la Neurona base con una compuerta OR: Si hay alta saturación (1) O sobrecarga (1) -> Alerta (1)
        double[][] entradasEntrenamiento = {
            {0, 0}, {0, 1}, {1, 0}, {1, 1}
        };
        int[] salidasEsperadas = {0, 1, 1, 1};

        Neurona cerebroIA = new Neurona(2, 0.1);
        cerebroIA.entrenar(entradasEntrenamiento, salidasEsperadas, 100);

        System.out.println("\n--- FASE 2: INICIALIZANDO ENJAMBRE INSTITUCIONAL ---");
        Enjambre bienestar = new Enjambre();
        // Se inyecta la misma IA entrenada a todos los profesionales
        bienestar.agregarProfesional(new ProfesionalBienestar("Psicólogo_1", 3, cerebroIA));
        bienestar.agregarProfesional(new ProfesionalBienestar("Psicólogo_2", 3, cerebroIA));
        bienestar.agregarProfesional(new ProfesionalBienestar("Médico_1", 4, cerebroIA));

        bienestar.imprimirEstado();

        System.out.println("--- PERTURBACIÓN: PICO ESTOCÁSTICO DE EMERGENCIAS ---");
        // Se satura el canal del Psicólogo 1, forzando a la neurona a predecir la falla y al enjambre a reorganizarse
        bienestar.getColmena().get(0).recibirCasos(5, bienestar); 
        bienestar.imprimirEstado();

        System.out.println("--- ESTABILIZACIÓN Y RETRACCIÓN RUDERAL ---");
        for (int dia = 1; dia <= 3; dia++) {
            System.out.println("Ciclo operativo " + dia + ":");
            bienestar.avanzarTiempo();
            bienestar.imprimirEstado();
        }
    }
}