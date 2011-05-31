#!/usr/bin/perl
# marc2mods.pl
# robyj@cc.umanitoba.ca
# 08-04-11
#
# converts a file of MARC records into MODS
use File::Copy;
use MARC::Batch;
use HTML::Entities;
use Encode;
use Date::Manip;

my $batch = MARC::Batch->new('USMARC', $ARGV[0]);
$batch->strict_off();
open( modfile, ">mods_book.xml") || die( "could not create MODS file" );
print modfile
      "<mods:mods xmlns:mods=\"http://www.loc.gov/mods/v3\" xmlns:xlink=\"http://www.w3.org/1999/xlink\"\n" .
      "\txmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" version=\"3.4\"\n" .
      "\txsi:schemaLocation=\"http://www.loc.gov/mods/v3 http://www.loc.gov/standards/mods/v3/mods-3-0.xsd\">\n";
while (my $record = $batch->next()) {
      
      # 245 field - <title>,<titleInfo>
      my $field245a = $record->field('245')->subfield('a');
      my $field245b = $record->field('245')->subfield('b');
      print modfile
            "\t<mods:titleInfo>\n" .
            "\t\t<mods:title>" .
            encode_entities(decode("UTF-8",$field245a)) .
            "</mods:title>\n" .
            "\t\t<mods:subTitle>" .
            encode_entities(decode("UTF-8",$field245b)) .
            "</mods:subTitle>\n" .
            "\t</mods:titleInfo>\n";
     
      # 700 field - <name> i think
      my @field700set = $record->field('700');
      foreach $field700 (@field700set) {
        my $field700a = $field700->subfield('a');
        my $surname = substr($field700a,0,index($field700a,","));
        my $firstname = substr( $field700a, index($field700a,",")+2,(length($field700a)-(index($field700a,",")+2))-1);
        my $field700d = $field700->subfield('d');
        # robyj - 200511 - remove period from end of date
        if (rindex($field700d,'.') != -1) {
          $field700d = substr($field700d,0,-1);
        }
        print modfile
              "\t<mods:name authority=\"naf\" type=\"personal\">\n" .
              "\t\t<mods:namePart type=\"family\">" .
              encode_entities(decode("UTF-8",$surname)) .
              "</mods:namePart>\n";
        print modfile
              "\t\t<mods:namePart type=\"given\">" .
              encode_entities(decode("UTF-8",$firstname)) .
              "</mods:namePart>\n";
        print modfile
              "\t\t<mods:namePart type=\"date\">" .
              UnixDate(ParseDate(encode_entities(decode("UTF-8",$field700d))),'%Y-%m-%dT00:00:00Z').
              "</mods:namePart>\n" .
              "\t</mods:name>\n";
     }
      # 260 - <originInfo>
      my $field260a = $record->field('260')->subfield('a');
      my $field260b = $record->field('260')->subfield('b');
      my $field260c = $record->field('260')->subfield('c');
      # robyj - 300511 - remove period from date if ness.
      if (index($field260c,'.') != -1) {
        $field260c = substr($field260c,0,-1);
      }
      print modfile
            "\t<mods:originInfo>\n" .
            "\t\t<mods:place>\n" .
            "\t\t\t<mods:placeTerm type=\"text\">" .
            encode_entities(decode("UTF-8",$field260a)) .
            "</mods:placeTerm>\n" .
            "\t\t</mods:place>\n" .
            "\t\t<mods:publisher>" .
            encode_entities(decode("UTF-8",$field260b)) .
            "</mods:publisher>\n" .
            "\t\t<mods:dateIssued>" .
            UnixDate(ParseDate(encode_entities(decode("UTF-8",$field260c))),'%Y-%m-%dT00:00:00Z').
            "</mods:dateIssued>\n" .
            "\t</mods:originInfo>\n";
      # 300 field - <extent>
      my $field300a = $record->field('300')->subfield('a');
      my $field300c = $record->field('300')->subfield('c');
      print modfile
            "\t<mods:physicalDescription>\n" .
            "\t\t<mods:extent>" .
            encode_entities(decode("UTF-8",$field300a)) . encode_entities(decode("UTF-8",$field300c)) .
            "</mods:extent>\n" .
            "\t</mods:physicalDescription>\n";
      #500 field - <notes>
      my @field500a = $record->field('500')->subfield('a');
      foreach my $field500 (%field500a) {
        print modfile
              "\t<mods:note>" .
              encode_entities(decode("UTF-8",$field500)) .
              "</mods:note>\n";
      }
      #503 field - <note> i think
     if($record->field('503'))
      {
	      my @field503a = $record->field('503')->subfield('a');
	      foreach my $field503atmp (%field503a) {
	        print modfile
	              "\t<mods:note>" .
	              encode_entities(decode("UTF-8",$field503atmp)) .
	              "<\mods:note>\n";
	      }
      }

      # 590 field(s) - <note> i think
      if($record->field('590'))
      {
	      my @field590 = $record->field('590')->subfield('a');
	      foreach $field590a (%field590) {
	        print modfile
	              "\t<mods:note>" .
	              encode_entities(decode("UTF-8",$field590a)) .
	              "</mods:note>\n";
	      }
      }
      # 008 field - whole bunch of fields stuck together
      # 001 field - <recordIdentifier>
      my $field001 = $record->field('001');
      print modfile
            "\t<mods:recordInfo>\n" .
           "\t\t<mods:recordIdentifier>" .
            encode_entities(decode("UTF-8",$field001->as_string())) .
            "</mods:recordIdentifier>\n";
      # 040 field - <recordContentSource>,<languageofCataloging>
      my $field040a = $record->field('040')->subfield('a');
      my $field040b = $record->field('040')->subfield('b');
      print modfile
            "\t\t<mods:recordContentSource>" .
            encode_entities(decode("UTF-8",$field040a)) .
            "</mods:recordContentSource>\n";
      print modfile
            "\t\t<mods:languageofCataloging>" .
            encode_entities(decode("UTF-8",$field040b)) .
            "</mods:languageofCataloging>\n" .
            "\t</mods:recordInfo>\n";
      # 130 field - <
  print modfile
        "</mods:mods>\n";
  close(modfile);
} 