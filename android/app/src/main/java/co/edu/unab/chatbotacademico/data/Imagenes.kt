package co.edu.unab.chatbotacademico.data

import android.content.ContentResolver
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageDecoder
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri
import android.os.Build
import android.util.Base64
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import kotlin.math.roundToInt

data class Adjunto(val miniatura: Bitmap, val dataUrl: String)

private const val LADO_MAXIMO = 1280
private const val LADO_MINIATURA = 400

suspend fun prepararImagen(resolver: ContentResolver, uri: Uri): Adjunto = withContext(Dispatchers.IO) {
    val bitmap = if (Build.VERSION.SDK_INT >= 28) {
        ImageDecoder.decodeBitmap(ImageDecoder.createSource(resolver, uri)) { decoder, info, _ ->
            val (ancho, alto) = dimensiones(info.size.width, info.size.height, LADO_MAXIMO)
            decoder.setTargetSize(ancho, alto)
            decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
        }
    } else {
        decodificarImagenAnterior(resolver, uri)
    }

    val bytes = ByteArrayOutputStream()
    if (!bitmap.compress(Bitmap.CompressFormat.JPEG, 80, bytes)) {
        throw IOException("No se pudo preparar la imagen.")
    }
    val jpeg = bytes.toByteArray()
    val (ancho, alto) = dimensiones(bitmap.width, bitmap.height, LADO_MINIATURA)
    val miniatura = Bitmap.createScaledBitmap(bitmap, ancho, alto, true)
    if (miniatura !== bitmap) bitmap.recycle()
    Adjunto(miniatura, "data:image/jpeg;base64," + Base64.encodeToString(jpeg, Base64.NO_WRAP))
}

private fun decodificarImagenAnterior(resolver: ContentResolver, uri: Uri): Bitmap {
    val limites = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, limites) }
    if (limites.outWidth <= 0 || limites.outHeight <= 0) throw IOException("La imagen no se pudo leer.")

    val opciones = BitmapFactory.Options().apply {
        inSampleSize = 1
        while (maxOf(limites.outWidth, limites.outHeight) / inSampleSize > LADO_MAXIMO * 2) {
            inSampleSize *= 2
        }
    }
    val bitmap = resolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, opciones) }
        ?: throw IOException("La imagen no se pudo leer.")
    val exif = try {
        resolver.openInputStream(uri)?.use {
            ExifInterface(it).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
        }
    } catch (_: IOException) {
        null
    }
    val matriz = Matrix()
    when (exif) {
        ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> matriz.setScale(-1f, 1f)
        ExifInterface.ORIENTATION_ROTATE_180 -> matriz.setRotate(180f)
        ExifInterface.ORIENTATION_FLIP_VERTICAL -> matriz.setScale(1f, -1f)
        ExifInterface.ORIENTATION_TRANSPOSE -> { matriz.setRotate(90f); matriz.postScale(-1f, 1f) }
        ExifInterface.ORIENTATION_ROTATE_90 -> matriz.setRotate(90f)
        ExifInterface.ORIENTATION_TRANSVERSE -> { matriz.setRotate(270f); matriz.postScale(-1f, 1f) }
        ExifInterface.ORIENTATION_ROTATE_270 -> matriz.setRotate(270f)
    }
    val (ancho, alto) = dimensiones(bitmap.width, bitmap.height, LADO_MAXIMO)
    matriz.preScale(ancho.toFloat() / bitmap.width, alto.toFloat() / bitmap.height)
    val reducida = Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matriz, true)
    if (reducida !== bitmap) bitmap.recycle()
    return reducida
}

private fun dimensiones(ancho: Int, alto: Int, maximo: Int): Pair<Int, Int> {
    val escala = minOf(1.0, maximo.toDouble() / maxOf(ancho, alto))
    return (ancho * escala).roundToInt().coerceAtLeast(1) to (alto * escala).roundToInt().coerceAtLeast(1)
}

suspend fun cargarQr(baseUrl: String, ruta: String): Bitmap? = withContext(Dispatchers.IO) {
    val url = urlDeServicio(baseUrl, ruta)?.takeIf { it.encodedPath == "/api/qr" }
        ?: return@withContext null
    val conexion = url.toUrl().openConnection() as HttpURLConnection
    try {
        conexion.connectTimeout = 8_000
        conexion.readTimeout = 8_000
        conexion.instanceFollowRedirects = false
        if (conexion.responseCode != HttpURLConnection.HTTP_OK) return@withContext null
        conexion.inputStream.use { BitmapFactory.decodeStream(it) }
    } finally {
        conexion.disconnect()
    }
}
