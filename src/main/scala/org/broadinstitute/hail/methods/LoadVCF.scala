package org.broadinstitute.hail.methods

import org.broadinstitute.hail.vcf.BufferedLineIterator

import scala.io.Source
import org.apache.spark.SparkContext
import org.broadinstitute.hail.variant._
import org.broadinstitute.hail.Utils._
import org.broadinstitute.hail.vcf
import org.broadinstitute.hail.annotations._
import scala.collection.JavaConversions._
import scala.reflect.ClassTag

object LoadVCF {
  // FIXME move to VariantDataset
  def apply(sc: SparkContext,
    file: String,
    compress: Boolean = true,
    nPartitions: Option[Int] = None): VariantDataset = {

    require(file.endsWith(".vcf")
      || file.endsWith(".vcf.bgz")
      || file.endsWith(".vcf.gz"))

    val hConf = sc.hadoopConfiguration
    val headerLines = readFile(file, hConf) { s =>
      Source.fromInputStream(s)
        .getLines()
        .takeWhile(line => line(0) == '#')
        .toArray
    }

    val codec = new htsjdk.variant.vcf.VCFCodec()

    val header = codec.readHeader(new BufferedLineIterator(headerLines.iterator.buffered))
      .getHeaderValue
      .asInstanceOf[htsjdk.variant.vcf.VCFHeader]

    // FIXME get descriptions when HTSJDK is fixed to expose filter descriptions
    val filters: List[(String, String)] = header
      .getFilterLines
      .toList
      .map(line => (line.getID, ""))

    val infoSignatures = header
      .getInfoHeaderLines
      .toList
      .map(line => (line.getID, VCFSignature.parse(line)))
      .toMap

    val variantAnnotationSignatures: Annotations = Annotations(Map("info" -> infoSignatures,
      "filters" -> new SimpleSignature(Class[Set[String]]),
        "pass" -> new SimpleSignature(Class[Boolean]),
        "qual" -> new SimpleSignature(Class[Double]),
        "rsid" -> new SimpleSignature(Class[String])))

    val headerLine = headerLines.last
    assert(headerLine(0) == '#' && headerLine(1) != '#')

    val sampleIds = headerLine
      .split("\t")
      .drop(9)

    val headerLinesBc = sc.broadcast(headerLines)
    val genotypes = sc.textFile(file, nPartitions.getOrElse(sc.defaultMinPartitions))
      .mapPartitions { lines =>
        val reader = vcf.HtsjdkRecordReader(headerLinesBc.value)
        lines.filter(line => !line.isEmpty && line(0) != '#')
          .flatMap(reader.readRecord)
          .map { case (v, va, gs) =>
            val b = new GenotypeStreamBuilder(v, compress)
            for (g <- gs)
              b += g
            (v, va, b.result(): Iterable[Genotype])
          }
      }

    VariantSampleMatrix(VariantMetadata(filters, sampleIds,
      IndexedSeq.fill(sampleIds.length)(Annotations.empty()), Annotations.empty(),
      variantAnnotationSignatures), genotypes)
  }
}
