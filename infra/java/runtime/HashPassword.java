import java.nio.charset.StandardCharsets;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
public class HashPassword {
    public static void main(String[] args) throws Exception {
        String input = new String(System.in.readAllBytes(), StandardCharsets.UTF_8).stripTrailing();
        var encoder = PasswordEncoderFactories.createDelegatingPasswordEncoder();
        if (args.length == 1 && args[0].equals("--verify")) {
            String[] parts = input.split("\n", 2);
            if (parts.length != 2 || !encoder.matches(parts[0], parts[1]))
                throw new IllegalStateException("Synthetic password and saved hash do not match");
            System.out.print("verified");
            return;
        }
        if (input.length() < 24 || input.length() > 64) throw new IllegalArgumentException("Invalid synthetic password length");
        String encoded = encoder.encode(input);
        if (!encoder.matches(input, encoded)) throw new IllegalStateException("Synthetic password verification failed");
        System.out.print(encoded);
    }
}
