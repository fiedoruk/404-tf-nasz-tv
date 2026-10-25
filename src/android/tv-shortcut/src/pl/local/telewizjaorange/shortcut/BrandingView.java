package pl.local.telewizjaorange.shortcut;

import android.content.Context;
import android.graphics.Color;
import android.util.TypedValue;
import android.view.Gravity;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.TextView;

/** Presentation only: FIT_CENTER source image and status in its reserved 830..950 band. */
public final class BrandingView extends FrameLayout {
    private final TextView status;
    public BrandingView(Context context) {
        super(context);
        setBackgroundColor(Color.rgb(245, 243, 236));
        ImageView background = new ImageView(context);
        background.setScaleType(ImageView.ScaleType.FIT_CENTER);
        background.setImageResource(context.getResources().getIdentifier(
                "nasz_tv_launcher", "drawable", context.getPackageName()));
        background.setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);
        addView(background, new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT));
        status = new TextView(context);
        status.setText("Przygotowanie…");
        status.setTextColor(Color.rgb(23, 57, 66));
        status.setGravity(Gravity.CENTER);
        status.setSingleLine(true);
        status.setIncludeFontPadding(false);
        addView(status, new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT));
    }
    public TextView statusLabel() { return status; }
    @Override protected void onLayout(boolean changed, int left, int top, int right, int bottom) {
        super.onLayout(changed, left, top, right, bottom);
        int width = right - left, height = bottom - top;
        float scale = Math.min(width / 1920f, height / 1080f);
        float x = (width - 1920f * scale) / 2f;
        float y = (height - 1080f * scale) / 2f;
        int labelLeft = Math.round(x + 180f * scale);
        int labelTop = Math.round(y + 830f * scale);
        int labelRight = Math.round(x + 1740f * scale);
        int labelBottom = Math.round(y + 950f * scale);
        int bandHeight = Math.max(1, labelBottom - labelTop);
        float nominal = 32f * getResources().getDisplayMetrics().scaledDensity;
        status.setTextSize(TypedValue.COMPLEX_UNIT_PX, Math.min(nominal, bandHeight * .70f));
        status.measure(MeasureSpec.makeMeasureSpec(Math.max(1, labelRight - labelLeft), MeasureSpec.EXACTLY),
                MeasureSpec.makeMeasureSpec(bandHeight, MeasureSpec.EXACTLY));
        status.layout(labelLeft, labelTop, labelRight, labelBottom);
    }
}
