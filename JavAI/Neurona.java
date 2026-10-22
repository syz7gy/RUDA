import java.util.Random;

public class Neurona {
    private final double[] pesos;
    private double sesgo;
    private final double tasaAprendizaje;

    public Neurona(int numEntradas, double tasaAprendizaje) {
        this.tasaAprendizaje = tasaAprendizaje;
        this.pesos = new double[numEntradas];

        Random rand = new Random();
        for (int i=0; i < numEntradas; i++) {
            this.pesos[i] = rand.nextDouble() * 2 - 1;
        }
        this.sesgo = rand.nextDouble() * 2 -1;
    }

    private int funcionActivacion(double suma) {
        return suma >= 0 ? 1 : 0;
    }
    
    public int predecir(double[] entradas) {
        double suma = sesgo;
        for (int i=0; i < entradas.length; i++) {
            suma += entradas[i] * pesos[i];
        }
        return funcionActivacion(suma);
    }

    public void entrenar(double[][] entradas, int[] salidasEsperadas, int epocasMaximas) {
        for (int epoca=0; epoca<epocasMaximas; epoca++) {
            int erroresTotales = 0;

            for (int i=0; i<entradas.length; i++) {
                double[] entradaActual = entradas[i];
                int esperada = salidasEsperadas[i];
                int prediccion = predecir(entradaActual);

                int error = esperada - prediccion;
                erroresTotales += Math.abs(error);

                for (int j=0; j<pesos.length; j++) {
                    pesos[j] += tasaAprendizaje * error * entradaActual[j];
                }
                sesgo += tasaAprendizaje * error;
            }

            if (erroresTotales == 0) {
                System.out.println("Entrenamiento completado exitosamente en la época: " + (epoca + 1));
                break;
            }
        }
    }
}
