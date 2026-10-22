import java.util.Scanner;

public class Main {
    public static void main(String args[]) {
        //Datos de entrenamiento: Puerta lógica AND
        //Solo da 1 cuando AMBAS entradas son 1
        double [][] entradas = {
            {0, 0},
            {0, 1},
            {1, 0},
            {1, 1},
        };
        
        Scanner sc = new Scanner(System.in);
        System.out.println("Selecccione la compuerta lógica a estudiar:");
        System.out.println("1) AND \n2) OR");

        int[] respuestasEsperadas;

        int opcion = sc.nextInt();

        switch (opcion) {
            case 1:
                respuestasEsperadas = new int[]{0, 0, 0, 1};
                break;
            case 2:
                respuestasEsperadas = new int[]{0, 1, 1, 1};
                break;
            default:
                System.out.println("Opción inválida. Se utilizará AND por defecto.\n");
                respuestasEsperadas = new int[]{0, 0, 0, 1};
                break;
        }
        

        //Crear uan neurona con 2 entradas y una tasa de aprendizaje de 0.1
        Neurona miIA = new Neurona(2, 0.1);

        System.out.println("--- Iniciando entrenamiento de la IA ---");
        miIA.entrenar(entradas, respuestasEsperadas, 100);

        System.out.println("\n--- Probando la IA entrenada ---");
        for (double[]entrada : entradas) {
            int resultado = miIA.predecir(entrada);
            System.out.printf("Entrada: [%.0f, %.0f] -> Respuesta IA: %d\n", entrada[0], entrada[1], resultado);
        }
    }
}


