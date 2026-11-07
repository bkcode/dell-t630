import java.awt.*;
import java.awt.image.BufferedImage;
import javax.imageio.ImageIO;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.HexFormat;
public class RuntimeProbe {
 public static void main(String[] args) throws Exception {
  if(args.length!=1 || !System.getProperty("user.name").equals("finger")) throw new IllegalStateException("Expected nonroot finger runtime");
  var image=new BufferedImage(320,64,BufferedImage.TYPE_INT_RGB);
  var graphics=image.createGraphics();graphics.setColor(Color.WHITE);graphics.fillRect(0,0,320,64);graphics.setColor(Color.BLACK);graphics.setFont(new Font(Font.SANS_SERIF,Font.PLAIN,18));graphics.drawString("Dell Java 21 Runtime",12,38);graphics.dispose();
  var output=Path.of(args[0]);ImageIO.write(image,"png",output.toFile());
  String sha=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(output)));
  System.out.println("{\"java_version\":\""+System.getProperty("java.version")+"\",\"architecture\":\""+System.getProperty("os.arch")+"\",\"user\":\"finger\",\"headless_font_and_PNG\":true,\"PNG_sha256\":\""+sha+"\",\"business_application_started\":false}");
 }
}
