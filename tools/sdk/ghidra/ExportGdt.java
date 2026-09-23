// ExportGdt.java - dump a Ghidra data-type archive (.gdt) to JSON.
//
// Run headless (see run-export.cmd). Args: <archive.gdt> <out.json>
//
// Written for 0xC0000054/sc4-ghidra-symbols SimCity4.gdt, whose types were
// extracted from the Mac builds' debug symbols. Those layouts are MAC layouts:
// every offset / slot order printed here is a HYPOTHESIS for the Windows exe
// until checked against its bytes (MSVC orders overloads differently and its
// this-adjust offsets differ). The JSON says so in its header.
//@category SC4

import ghidra.app.script.GhidraScript;
import ghidra.program.model.data.*;
import java.io.*;
import java.util.*;

public class ExportGdt extends GhidraScript {

    private static String q(String s) {
        if (s == null) return "null";
        StringBuilder b = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            if (c == '"' || c == '\\') b.append('\\').append(c);
            else if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
            else b.append(c);
        }
        return b.append('"').toString();
    }

    private static String sig(FunctionDefinition f) {
        StringBuilder b = new StringBuilder();
        b.append(f.getReturnType() == null ? "?" : f.getReturnType().getDisplayName()).append(" (");
        ParameterDefinition[] ps = f.getArguments();
        for (int i = 0; i < ps.length; i++) {
            if (i > 0) b.append(", ");
            b.append(ps[i].getDataType().getDisplayName());
            if (ps[i].getName() != null) b.append(' ').append(ps[i].getName());
        }
        return b.append(')').toString();
    }

    @Override
    public void run() throws Exception {
        String[] a = getScriptArgs();
        File in = new File(a[0]), out = new File(a[1]);
        FileDataTypeManager dtm = FileDataTypeManager.openFileArchive(in, false);
        try (PrintWriter w = new PrintWriter(new OutputStreamWriter(new FileOutputStream(out), "UTF-8"))) {
            w.println("{\"source\":" + q(in.getName()) + ",");
            w.println("\"caveat\":\"MAC-build layouts from debug symbols; Windows offsets/slot order are hypotheses until byte-verified\",");
            w.println("\"types\":[");
            List<DataType> all = new ArrayList<>();
            dtm.getAllDataTypes().forEachRemaining(all::add);
            all.sort(Comparator.comparing(DataType::getPathName));
            boolean first = true;
            for (DataType dt : all) {
                StringBuilder b = new StringBuilder();
                b.append("{\"path\":").append(q(dt.getPathName()))
                 .append(",\"name\":").append(q(dt.getName()))
                 .append(",\"size\":").append(dt.getLength());
                if (dt.getDescription() != null && !dt.getDescription().isEmpty())
                    b.append(",\"desc\":").append(q(dt.getDescription()));
                if (dt instanceof Composite) {
                    Composite c = (Composite) dt;
                    b.append(",\"kind\":").append(q(dt instanceof Union ? "union" : "struct"));
                    b.append(",\"fields\":[");
                    DataTypeComponent[] cs = c.getDefinedComponents();
                    for (int i = 0; i < cs.length; i++) {
                        DataTypeComponent x = cs[i];
                        if (i > 0) b.append(',');
                        b.append("{\"off\":").append(x.getOffset())
                         .append(",\"len\":").append(x.getLength())
                         .append(",\"name\":").append(q(x.getFieldName()))
                         .append(",\"type\":").append(q(x.getDataType().getDisplayName()));
                        DataType t = x.getDataType();
                        if (t instanceof Pointer && ((Pointer) t).getDataType() instanceof FunctionDefinition)
                            b.append(",\"sig\":").append(q(sig((FunctionDefinition) ((Pointer) t).getDataType())));
                        if (x.getComment() != null) b.append(",\"comment\":").append(q(x.getComment()));
                        b.append('}');
                    }
                    b.append(']');
                } else if (dt instanceof ghidra.program.model.data.Enum) {
                    ghidra.program.model.data.Enum e = (ghidra.program.model.data.Enum) dt;
                    b.append(",\"kind\":\"enum\",\"values\":{");
                    String[] ns = e.getNames();
                    for (int i = 0; i < ns.length; i++) {
                        if (i > 0) b.append(',');
                        b.append(q(ns[i])).append(':').append(e.getValue(ns[i]));
                    }
                    b.append('}');
                } else if (dt instanceof FunctionDefinition) {
                    b.append(",\"kind\":\"func\",\"sig\":").append(q(sig((FunctionDefinition) dt)));
                } else if (dt instanceof TypeDef) {
                    b.append(",\"kind\":\"typedef\",\"base\":").append(q(((TypeDef) dt).getBaseDataType().getPathName()));
                } else {
                    b.append(",\"kind\":").append(q(dt.getClass().getSimpleName()));
                }
                b.append('}');
                w.println((first ? "" : ",") + b);
                first = false;
            }
            w.println("]}");
            println("ExportGdt: " + all.size() + " types -> " + out);
        } finally {
            dtm.close();
        }
    }
}
